import time
import sys


def convert_time_to_string(value):
    units = [
        (3600, "h"),
        (60, "m"),
        (1, "s"),
        (0.001, "ms"),
        (0.000001, "ns")
    ]

    for threshold, suffix in units:
        if value >= threshold:
            qty = value / threshold
            return f"{qty:.2f}{suffix}"

    return f"{value * 1000:.2f}ms"

class ProfilerValues:
    def __init__(self):
        self.times_called = 0
        self.all_time = 0
        self.min_time = None
        self.max_time = None

    def store(self, elapsed):
        self.times_called += 1
        self.all_time += elapsed

        if self.min_time is None:
            self.min_time = elapsed

        elif self.min_time > elapsed:
            self.min_time = elapsed

        if self.max_time is None:
            self.max_time = elapsed

        elif self.max_time < elapsed:
            self.max_time = elapsed

    def __str__(self):
        return f"Calls: {self.times_called}, Total: {convert_time_to_string(self.all_time)}, Average: {convert_time_to_string(self.all_time / self.times_called)}, Min: {convert_time_to_string(self.min_time)}, Max: {convert_time_to_string(self.max_time)}"

class Profiler:
    def __init__(self, target: object):
        self.__target = target
        self.__lookup = {}
        self.__start_times: dict[str, float] = {}

        self.reset_profiler()

    def tracer(self, frame, event, arg):
        if event == "call":
            self.__start_times[frame] = time.perf_counter()

        elif event == "return":
            start = self.__start_times.pop(frame, None)
            if start is not None:
                elapsed = time.perf_counter() - start
                key = (frame.f_code.co_filename,
                         frame.f_code.co_name,
                         frame.f_code.co_firstlineno)

                if key not in self.__lookup:
                    self.__lookup[key] = ProfilerValues()

                self.__lookup[key].store(elapsed)

        return self.tracer

    def output(self):
        print("Profiler Output:")

        keys = list(self.__lookup.keys())
        for key in keys:
            value = self.__lookup[key]
            #print('"' + str(key[0]) + ":"+str(key[2]) + '"' + " @ " + str(key[1]), ":", str(value))
            print(f"""File "{key[0]}", line {key[2]}, in {key[1]}: {str(value)}""")

    def reset_profiler(self):
        self.__lookup = {}
        self.__start_times = {}

        sys.setprofile(self.tracer)
        print("Profiler Connected")