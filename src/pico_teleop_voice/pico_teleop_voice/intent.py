"""Qwen3.5 0.9B intent parser: text → structured robot command JSON."""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个机器人语音控制助手。用户会用自然语言给出指令，你需要将其转换为JSON格式的机器人命令。

可用命令:
1. move - 移动机械臂末端
   {"action": "move", "arm": "left"|"right"|"both", "direction": [x,y,z], "distance": float_meters}
2. gripper - 控制夹爪
   {"action": "gripper", "arm": "left"|"right"|"both", "state": "open"|"close"}
3. record_start - 开始录制
   {"action": "record_start"}
4. record_stop - 停止录制
   {"action": "record_stop"}
5. switch_ik - 切换IK求解器
   {"action": "switch_ik", "solver": "curobo"|"moveit"|"trac_ik"}
6. switch_arm - 切换机器人
   {"action": "switch_arm", "arm_name": string}
7. home - 回到初始位置
   {"action": "home", "arm": "left"|"right"|"both"}
8. stop - 紧急停止
   {"action": "stop"}
9. scale - 调整工作空间缩放
   {"action": "scale", "value": float}
10. speak - 非指令性对话，需要语音回复
    {"action": "speak", "text": "回复内容"}

方向约定: x=前, -x=后, y=左, -y=右, z=上, -z=下
距离单位: 米 (默认0.05m即5cm)

只输出JSON，不要其他文字。"""


class IntentParser:
    def __init__(
        self,
        model_name: str = "Qwen/Qwen2.5-0.5B-Instruct",
        device: str = "cuda:0",
        max_new_tokens: int = 128,
    ):
        self._model_name = model_name
        self._device = device
        self._max_new_tokens = max_new_tokens
        self._model = None
        self._tokenizer = None

    def load(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info(f"Loading intent model: {self._model_name}")
        self._tokenizer = AutoTokenizer.from_pretrained(self._model_name, trust_remote_code=True)
        self._model = AutoModelForCausalLM.from_pretrained(
            self._model_name,
            torch_dtype="auto",
            device_map=self._device,
            trust_remote_code=True,
        )
        logger.info("Intent model loaded")

    def parse(self, text: str) -> Optional[dict]:
        if not text or not text.strip():
            return None
        if self._model is None:
            raise RuntimeError("Model not loaded. Call load() first.")

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ]

        input_text = self._tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self._tokenizer(input_text, return_tensors="pt").to(self._device)

        outputs = self._model.generate(
            **inputs,
            max_new_tokens=self._max_new_tokens,
            do_sample=False,
        )

        response = self._tokenizer.decode(
            outputs[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        ).strip()

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    return json.loads(response[start:end])
                except json.JSONDecodeError:
                    pass
            logger.warning(f"Failed to parse intent JSON: {response}")
            return {"action": "speak", "text": response}
