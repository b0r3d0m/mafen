import logging
import logging.handlers
import os
import errno


class LogFormatter(logging.Formatter):
    info_fmt = '%(levelname)-4.4s|%(asctime)s| %(message)s'
    warn_fmt = info_fmt
    err_fmt = '%(levelname)-4.4s|%(asctime)s|%(module)s|%(funcName)s|%(lineno)d %(message)s'
    crit_fmt = err_fmt

    def __init__(self, fmt='%(levelname)-4.4s|%(msg)s'):
        logging.Formatter.__init__(self, fmt)

    def format(self, record):
        # Save the original format configured by the user
        # when the logger formatter was instantiated
        format_orig = self._fmt

        # Replace the original format with one customized by logging level
        if record.levelno == logging.INFO:
            self._fmt = LogFormatter.info_fmt

        elif record.levelno == logging.WARNING:
            self._fmt = LogFormatter.warn_fmt

        elif record.levelno == logging.ERROR:
            self._fmt = LogFormatter.err_fmt

        elif record.levelno == logging.CRITICAL:
            self._fmt = LogFormatter.crit_fmt

        # Call the original formatter class to do the grunt work
        result = logging.Formatter.format(self, record)

        # Restore the original format configured by the user
        self._fmt = format_orig

        return result


class SimpleLogger(object):
    def __init__(self):
        self.root_logger = logging.getLogger(self.__class__.__name__)

        if len(self.root_logger.handlers) != 0:
            return

        self.root_logger.setLevel(logging.INFO)

        dir = os.path.dirname(os.path.abspath(__file__))
        logs_path = os.path.join(dir, 'logs')
        if not os.path.exists(logs_path):
            try:
                os.makedirs(logs_path)
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise
                pass

        fh = logging.handlers.TimedRotatingFileHandler(os.path.join(logs_path, 'log_'), when='midnight')
        fh.setFormatter(LogFormatter())
        self.root_logger.addHandler(fh)

        ch = logging.StreamHandler()
        ch.setFormatter(LogFormatter())
        self.root_logger.addHandler(ch)

    def info(self, msg):
        self.root_logger.info(msg)

    def warning(self, msg):
        self.root_logger.warning(msg)

    def error(self, msg):
        self.root_logger.error(msg)

    def critical(self, msg):
        self.root_logger.critical(msg)
