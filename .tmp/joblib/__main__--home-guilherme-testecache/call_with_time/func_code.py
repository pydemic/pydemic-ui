# first line: 9
    @memory.cache
    def call_with_time(*args, **kwargs):
        clock, fn, *args = args
        return (clock(), fn(*args, **kwargs))
