# from transformers import AutoTokenizer, AutoModelForCausalLM
# import torch


# class Gemma7B(object):
#     def __init__(self):
#         self.access_token = "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"
#         self.tokenizer = AutoTokenizer.from_pretrained("google/gemma-7b")
#         self.model = AutoModelForCausalLM.from_pretrained(
#             "google/gemma-7b",
#             device_map="auto",
#             torch_dtype=torch.float16,
#             token=self.access_token,
#         )

#     def think(self, msg: str):
#         input_text = str(msg)
#         input_ids = self.tokenizer(input_text, return_tensors="pt").to("cuda")

#         outputs = self.model.generate(**input_ids, max_length=1000)
#         res = self.tokenizer.decode(outputs[0])
#         try:
#             res = res.split("Answer:")[1]
#             res = res.split("<eos>")[0]
#             res = res.strip()
#             return res
#         except Exception as e:
#             return res
