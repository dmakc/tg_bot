import datetime
import logging
import os
import time
from http import HTTPStatus

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

logging.basicConfig(
    level=logging.DEBUG,
    filename='bot.log',
    filemode='w',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)
logger.addHandler(
    logging.StreamHandler()
)


class HTTPStatusError(Exception):
    """Сервер вернул ошибку."""


class UndocumentedStatusError(Exception):
    """Недокументированный статус."""


class EmptyDictOrListError(Exception):
    """Пустой словарь или список."""


class EmptyResponseFromAPI(Exception):
    """Пустой ответ от API."""


def check_tokens():
    """Проверяем наличие токена."""
    tokens = True
    if PRACTICUM_TOKEN is None:
        tokens = False
        logger.critical('Отсутствует откружение: PRACTICUM_TOKEN')
    if TELEGRAM_TOKEN is None:
        tokens = False
        logger.critical('Отсутствует откружение: TELEGRAM_TOKEN')
    if TELEGRAM_CHAT_ID is None:
        tokens = False
        logger.critical('Отсутствует откружение: CHAT_ID')
    return tokens


def send_message(bot, message):
    """Отправляем сообщение в бот."""
    try:
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logger.debug(f'Сообщение в telegram было отправлено: {message}')
    except telegram.TelegramError as error:
        logger.error(f'Сообщение в telegram не отправлено: {error}')


def get_api_answer(timestamp):
    """Делаем запрос к API."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            logger.error(f'API недоступен: {response.status_code}')
            raise HTTPStatusError(f'API недоступен: {response.status_code}')
        return response.json()
    except Exception as error:
        logger.error(f'Код ответа API: {error}')
        raise Exception(f'Код ответа API: {error}')


def check_response(response):
    """Проверяем ответ."""
    logger.debug('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise EmptyResponseFromAPI('Пустой ответ от API')
    if not isinstance(response['homeworks'], list):
        raise TypeError('homeworks не является списком')
    if not isinstance(response['current_date'], int):
        raise TypeError('current_date не является списком')
    return response['homeworks']


def parse_status(homework):
    """Извлекаем статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise UndocumentedStatusError(
            f'Неизвестный статус работы - {homework_status}'
        )
    return (
        'Изменился статус проверки работы "{homework_name}". {verdict}'
    ).format(
        homework_name=homework_name,
        verdict=HOMEWORK_VERDICTS[homework_status]
    )


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical('Отсутствуют переменные окружения')
        exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    now = datetime.datetime.now()
    send_message(
        bot,
        f'Начало работы telegram бота: {now.strftime("%d-%m-%Y %H:%M")}'
    )
    while True:
        try:
            response = get_api_answer(timestamp)
            if check_response(response):
                for homework in response['homeworks']:
                    message = parse_status(homework)
                    send_message(bot, message)
        except Exception as error:
            logger.error(f'Сбой в работе бота: {error}')
            message = f'Сбой в работе бота: {error}'
            send_message(bot, message)
        finally:
            logger.info('Ждем 10 минут и проверяем статус')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
