from abc import ABC, abstractmethod

class ChatBot(ABC): 

    @abstractmethod
    def __init__(self):
        pass

    @abstractmethod
    def send_message(self, message):
        pass

    @abstractmethod
    def get_messages(self):
        pass

    @abstractmethod
    def run(self):
        pass