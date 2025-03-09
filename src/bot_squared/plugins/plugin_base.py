from queue import Queue


class PluginBase:
    def __init__(self):
        self.function_queue = Queue[dict]()

    def add_to_queue(self, function_name: str, args: dict):
        self.function_queue.put({"function_name": function_name, "args": args})

    def handle_integration_function_queue(self):
        while not self.function_queue.empty():
            item = self.function_queue.get()

            if "function_name" not in item:
                self.logger.error("Error: function_name not in item")
                continue

            if "args" not in item:
                self.logger.error("Error: args not in item")
                continue

            function_name = item["function_name"]
            args = item["args"]
            try:
                requested_function = getattr(self, function_name)

                # Execute the requested function
                requested_function(**args)
            except AttributeError as e:
                self.logger.error(f"Error: {e}")
                return
