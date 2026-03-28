import logging
import sys

def setup_logger():
    
    logger = logging.getLogger("app") 
    logger.setLevel(logging.DEBUG) # captura todos los errores superiores o igual a debug

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG) # handler para consola
    
    file_handler = logging.FileHandler("logs.txt")
    file_handler.setLevel(logging.ERROR) # handler para archivo
    
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    ) # especifico el formato que tendran los logs
    
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler) 
    logger.addHandler(file_handler) # anyado ambos handlers
    
    return logger