class NotEnoughItems(Exception):
    pass


class AgentDoesNotExist(Exception):
    pass


class InsufficientBalance(Exception):
    pass


class NoOrderMatch(Exception):
    pass


class WrongOrderType(Exception):
    pass


class DuplicateBuyOrder(Exception):
    def __init__(self, message: str, order_id: int):
        super().__init__(message)
        self.order_id = order_id
