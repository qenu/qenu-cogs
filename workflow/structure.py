from dataclasses import dataclass
from typing import Optional

PAYMENT_TYPE: dict = {
    0: "轉帳",
    1: "歐富寶",
    2: "paypal",
    3: "其他",
}

COMM_STATUS_TYPE: dict = {
    0: "等待",
    1: "草稿",
    2: "線搞",
    3: "上色",
    4: "完工",
}

COMM_TYPE: dict = {
    "客製貼圖": 650,
    "訂閱徽章": 550,
    "小奇點圖": 550,
    "資訊大圖": 700,
    "實況圖層": 0,
    "其他委託": 0,
}

COMM_DATA: dict = {
    "type": None,
    "count": 0,
}

QUOTE_STATUS_TYPE: dict = {
    0: "取消",
    1: "等待中",
    2: "進行中",
    3: "已完成",
}

class Commission:
    def __init__(self, *, _type: str, _count: int = 0, per: int = 0) -> None:
        self._type = _type
        self._count = _count
        self.per = COMM_TYPE.get(_type, per)
        self._status = COMM_STATUS_TYPE[0]

@dataclass
class CommissionData:
    commission: list

    def total(self) -> str:
        return_str = ""
        for item in self.commission:
            if item.count != 0:
                return_str += f"{item._type} x{item._count} = {(item._count * item.per) or '報價'}\n"
        return return_str

@dataclass
class CustomerData:
    name: str # 委託人姓名
    contact: str # 聯絡方式
    request_date: int # 委託日期
    payment_method: int # 付款方式
    contact_info: str = "" # 委託人聯絡資訊

@dataclass
class Quote:
    status: int # 委託狀態
    last_update: int # 最後更新時間
    estimate_start_date: int # 預計開始日期
    customer_data: CustomerData
    comm_data: CommissionData
    message_id: str # discord.Message.id


# QUOTE_DATA: dict = {
#             "customer_data": {
#                 "name": None,
#                 "contact": None,
#                 "request_date": 0,
#                 "payment_method": None
#             },
#             "quote_data": {
#                 "quotation": [],
#                 "total": 0,
#             },
#             "status": None,
#             "estimate_start_date": None,
#             "last_update": None,
#             "message": None,
#             "message_id": None,
#         }
