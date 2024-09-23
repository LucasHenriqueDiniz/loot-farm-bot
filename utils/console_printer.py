from datetime import datetime

from colorama import Fore, Style, init

# Inicializa o colorama para suporte no Windows
init()

# Mapeamento de cores usando constantes do colorama
color_map = {
    "ERROR": Fore.RED,
    "INFO": Fore.BLUE,
    "SUCCESS": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "TIME": Fore.LIGHTBLACK_EX,  # Para cinza, usando light black
    "RESET": Style.RESET_ALL,
    "BOLD": Style.BRIGHT,
    "DIM": Style.DIM,
    "NORMAL": Style.NORMAL,
    "TIME": Fore.MAGENTA,
}


def print_console(message, msg_type="INFO", noTime=False):
    """Imprime uma mensagem formatada no console com o tipo de mensagem colorido.

    Args:
        message (str): A mensagem a ser impressa.
        msg_type (str, opcional): O tipo de mensagem (ex: "INFO", "ERROR", "SUCCESS", "WARNING").
            Padrão é "INFO".

    Returns:
        None
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if not noTime else ""

    # Obtém a cor correspondente ao tipo de mensagem, padrão para azul (INFO)
    color = color_map.get(msg_type.upper(), Fore.BLUE)

    # Imprime a mensagem formatada com a cor e estilo apropriados
    print(
        f"{color}[{msg_type.upper()}] {Style.RESET_ALL}{message} {color_map['TIME']}| {current_time}{Style.RESET_ALL}"
    )


def print_measured_time(func_name, elapsed_time):
    """Imprime o tempo de execução de uma função.

    Args:
        func_name (str): O nome da função.
        elapsed_time (float): O tempo de execução da função.

    Returns:
        None
    """

    print_console(
        f"{func_name} levou {elapsed_time:.2f} segundos para ser executada.",
        "TIME",
        noTime=True,
    )


def create_error_file(error, error_type):
    """Cria um arquivo de erro com a mensagem de erro, tipo de erro e a data atual e salva na pasta 'logs'.

    Args:
        error (str): A mensagem de erro.
        error_type (str): O tipo de erro.

    Returns:
        None
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    file_name = f"logs/ERROR_{error_type}_{current_time}.txt"

    with open(file_name, "w") as f:
        f.write(error)

    print_console(f"Erro salvo em {file_name}", "ERROR")


def create_log_file(log, log_type):
    """Cria um arquivo de log com a mensagem de log, tipo de log e a data atual e salva na pasta 'logs'.

    Args:
        log (str): A mensagem de log.
        log_type (str): O tipo de log.

    Returns:
        None
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    file_name = f"logs/LOG_{log_type}_{current_time}.txt"

    with open(file_name, "w") as f:
        f.write(log)

    print_console(f"Log salvo em {file_name}", "INFO")
