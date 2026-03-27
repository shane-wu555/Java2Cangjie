import os
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import BitsAndBytesConfig


def make_prompt(instruction: str, input_text: str) -> str:
    if input_text and input_text.strip():
        return f"### 指令：\n{instruction.strip()}\n### 输入：\n{input_text.strip()}\n### 输出：\n"
    return f"### 指令：\n{instruction.strip()}\n### 输出：\n"


def preprocess(examples, tokenizer, max_source_length=2048, max_target_length=2048):
    input_texts = []
    target_texts = []

    for ins, inp, out in zip(examples["instruction"], examples.get("input", []), examples["output"]):
        input_texts.append(make_prompt(ins, inp))
        target_texts.append(out.strip())

    model_inputs = tokenizer(
        input_texts,
        max_length=max_source_length,
        padding="max_length",
        truncation=True,
    )

    # For decoder-only models like Qwen2, we don't need separate target tokenization
    # The labels are the same as input_ids for causal language modeling
    model_inputs["labels"] = model_inputs["input_ids"].copy()

    return model_inputs


if __name__ == "__main__":
    model_name = os.environ.get("BASE_MODEL", r"D:\models\Qwen2.5-Coder-7B-Instruct")
    output_dir = os.environ.get("LORA_OUTPUT", "outputs/qwen2.5b-instruct-lora")

    print(f"Base Model: {model_name}")
    print(f"LoRA Output: {output_dir}")
    print("Loading tokenizer and dataset...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

    ds = load_dataset(
        "json",
        data_files={
            "train": "finetune_dataset/train.alpaca.jsonl",
            "valid": "finetune_dataset/valid.alpaca.jsonl",
        },
    )

    print("Configuring 4-bit quantization and model for training...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype="float16",
    )

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is not available. 请先安装 CUDA 驱动并检查 torch.cuda.is_available() 是否为 True")

    # 强制将模型加载到 GPU 上（CUDA:0）
    device_map = {"": "cuda:0"}

    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map=device_map,
        torch_dtype=torch.float16,
        trust_remote_code=True,
    )

    model.to("cuda")

    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=8,
        lora_alpha=32,
        target_modules=["q_proj", "v_proj", "o_proj", "k_proj"],
        lora_dropout=0.1,
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)

    print("Preprocessing dataset...")
    tokenized = ds.map(
        lambda x: preprocess(x, tokenizer),
        batched=True,
        remove_columns=ds["train"].column_names,
    )

    training_args = TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=4,
        per_device_eval_batch_size=4,
        gradient_accumulation_steps=2,
        warmup_steps=100,
        num_train_epochs=2,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=200,
        save_strategy="steps",
        save_steps=400,  # 改为200的倍数
        save_total_limit=3,
        load_best_model_at_end=True,
        metric_for_best_model="loss",
        weight_decay=0.01,
        gradient_checkpointing=True,
        deepspeed=None,
        report_to="none",
        remove_unused_columns=False,
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
    os.makedirs(output_dir, exist_ok=True)
    trainer.save_model(output_dir)

    print("Finetuning complete. Path:", output_dir)
