import os
import torch
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    TrainingArguments,
    Trainer,
    BitsAndBytesConfig,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training


def make_prompt(instruction: str, input_text: str) -> str:
    instruction = (instruction or "").strip()
    input_text = (input_text or "").strip()

    if input_text:
        return (
            f"### 指令：\n{instruction}\n"
            f"### 输入：\n{input_text}\n"
            f"### 输出：\n"
        )
    return f"### 指令：\n{instruction}\n### 输出：\n"


def preprocess(examples, tokenizer, max_length=2048):
    instructions = examples["instruction"]
    outputs = examples["output"]
    inputs = examples["input"] if "input" in examples else [""] * len(instructions)

    all_input_ids = []
    all_attention_mask = []
    all_labels = []

    for ins, inp, out in zip(instructions, inputs, outputs):
        prompt = make_prompt(ins, inp)
        answer = ((out or "").strip()) + tokenizer.eos_token

        prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
        answer_ids = tokenizer(answer, add_special_tokens=False)["input_ids"]

        input_ids = prompt_ids + answer_ids
        labels = [-100] * len(prompt_ids) + answer_ids
        attention_mask = [1] * len(input_ids)

        if len(input_ids) > max_length:
            input_ids = input_ids[:max_length]
            labels = labels[:max_length]
            attention_mask = attention_mask[:max_length]

        pad_len = max_length - len(input_ids)
        if pad_len > 0:
            input_ids = input_ids + [tokenizer.pad_token_id] * pad_len
            labels = labels + [-100] * pad_len
            attention_mask = attention_mask + [0] * pad_len

        all_input_ids.append(input_ids)
        all_labels.append(labels)
        all_attention_mask.append(attention_mask)

    return {
        "input_ids": all_input_ids,
        "attention_mask": all_attention_mask,
        "labels": all_labels,
    }


def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))

    model_name = os.environ.get("BASE_MODEL", r"D:\models\Qwen2.5-Coder-7B-Instruct")
    output_dir = os.environ.get("LORA_OUTPUT", os.path.join(project_dir, "outputs", "qwen2.5b-instruct-lora"))

    train_file = os.environ.get("TRAIN_FILE", os.path.join(project_dir, "data", "train.alpaca.max2048.jsonl"))
    valid_file = os.environ.get("VALID_FILE", os.path.join(project_dir, "data", "valid.alpaca.max2048.jsonl"))

    max_length = int(os.environ.get("MAX_LENGTH", 2048))
    per_device_train_batch_size = int(os.environ.get("TRAIN_BATCH_SIZE", 1))
    per_device_eval_batch_size = int(os.environ.get("EVAL_BATCH_SIZE", 1))
    gradient_accumulation_steps = int(os.environ.get("GRAD_ACC_STEPS", 1))
    num_train_epochs = int(os.environ.get("NUM_TRAIN_EPOCHS", 1))
    learning_rate = float(os.environ.get("LEARNING_RATE", 2e-4))

    print("=" * 80)
    print(f"Base Model   : {model_name}")
    print(f"Output Dir   : {output_dir}")
    print(f"Train File   : {train_file}")
    print(f"Valid File   : {valid_file}")
    print(f"Max Length   : {max_length}")
    print(f"Train Batch  : {per_device_train_batch_size}")
    print(f"Eval Batch   : {per_device_eval_batch_size}")
    print(f"Grad Acc     : {gradient_accumulation_steps}")
    print(f"Epochs       : {num_train_epochs}")
    print(f"Learning Rate: {learning_rate}")
    print("=" * 80)

    if not os.path.exists(train_file):
        raise FileNotFoundError(f"训练集不存在: {train_file}")
    if not os.path.exists(valid_file):
        raise FileNotFoundError(f"验证集不存在: {valid_file}")

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available. 请先检查 GPU / CUDA / PyTorch 环境。")

    print("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    print("Loading dataset...")
    ds = load_dataset(
        "json",
        data_files={
            "train": train_file,
            "valid": valid_file,
        },
    )

    print(ds)

    print("Configuring 4-bit quantization...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
    )

    print("Loading model...")
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map={"": "cuda:0"},
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    model.config.use_cache = False
    model.config.pad_token_id = tokenizer.pad_token_id

    print("Preparing model for k-bit training...")
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=8,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM",
    )

    print("Applying LoRA...")
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    print("Tokenizing dataset...")
    tokenized = ds.map(
        lambda x: preprocess(x, tokenizer, max_length=max_length),
        batched=True,
        remove_columns=ds["train"].column_names,
        desc="Preprocessing dataset",
    )

    print("Sample check...")
    sample = tokenized["train"][0]
    print("input_ids length      :", len(sample["input_ids"]))
    print("attention_mask length :", len(sample["attention_mask"]))
    print("labels length         :", len(sample["labels"]))

    os.makedirs(output_dir, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=2,
        warmup_steps=100,
        num_train_epochs=num_train_epochs,
        learning_rate=learning_rate,
        fp16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=100,
        save_total_limit=3,
        load_best_model_at_end=False,
        weight_decay=0.01,
        gradient_checkpointing=True,
        report_to="none",
        remove_unused_columns=False,
        dataloader_pin_memory=False,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=tokenized["train"],
        eval_dataset=tokenized["valid"],
    )

    print("Starting training...")
    trainer.train()

    print("Saving trained LoRA model...")
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    print("Finetuning complete.")
    print("Saved to:", output_dir)


if __name__ == "__main__":
    main()