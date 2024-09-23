import time

from colorama import Fore, Style


def measure_time(func):
    def wrapper(*args, **kwargs):

        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        message = f"{Fore.LIGHTBLACK_EX}[TIME] {Fore.BLUE}{func.__name__} took {elapsed_time} seconds"
        message += Fore.RESET
        print(message)
        return result

    return wrapper
