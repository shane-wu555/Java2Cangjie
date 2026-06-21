"""Shared prompt contract for training, evaluation, and serving."""

INSTRUCTION = "将Java代码转换为仓颉代码。只输出仓颉代码，不要解释。"

CONVERSION_RULES = """转换规则：
1. Java 基本类型映射：int→Int32, long→Int64, float→Float32, double→Float64, boolean→Bool, byte→Byte, char→Char。
2. struct/class 的公有字段使用 PascalCase；局部变量、参数和函数名保持 camelCase。
3. 构造方法使用 this 引用成员；去掉 new，直接调用构造器。
4. interface 默认方法直接使用 func，不添加 open。
5. System.out.println(x) 转换为 println(x)。
6. public static void main(String[] args) 转换为 main(): Unit。
7. 局部绑定不重新赋值时使用 let，仅在变量本身重新赋值时使用 var。"""


def make_prompt(input_text: str, instruction: str = INSTRUCTION) -> str:
    return (
        f"### 指令：\n{(instruction or INSTRUCTION).strip()}\n"
        f"{CONVERSION_RULES}\n"
        f"### 输入：\n{(input_text or '').strip()}\n"
        "### 输出：\n"
    )
