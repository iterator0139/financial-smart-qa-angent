class ContextManager:
    def __init__(self):
        self.contexts = {}

    def add_context(self, context):
        self.contexts[context.id] = context

    def get_context(self, id):
        return self.contexts[id]