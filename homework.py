import datetime
import logging
import sys
import os
import time
from http import HTTPStatus

import exceptions
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


def check_tokens():
    """Проверяем наличие токена."""
    return all([TELEGRAM_TOKEN, PRACTICUM_TOKEN, TELEGRAM_CHAT_ID])


def send_message(bot, message):
    """Отправляем сообщение в бот."""
    try:
        logging.info('Начало отправки сообщения в telegram')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение в telegram было отправлено: {message}')
    except telegram.TelegramError as error:
        logging.error(f'Сообщение в telegram не отправлено: {error}')


def get_api_answer(timestamp):
    """Делаем запрос к API."""
    params_request = {
        'url': ENDPOINT,
        'headers': HEADERS,
        'params': {'from_date': timestamp},
    }
    try:
        logging.info(
            'Начало запроса: url = {url},'
            'headers = {headers},'
            'params = {params}'.format(**params_request))
        response = requests.get(**params_request)
        if response.status_code != HTTPStatus.OK:
            raise exceptions.InvalidResponseCode(
                'Не удалось получить ответ API, '
                f'ошибка: {response.status_code}'
                f'причина: {response.reason}'
                f'текст: {response.text}')
        return response.json()
    except requests.exceptions.RequestException as error:
        logging.error(f'Ошибка запроса: {error}')
        raise exceptions.RequestFailed()


def check_response(response):
    """Проверяем ответ."""
    logging.debug('Начало проверки ответа API')
    if not isinstance(response, dict):
        raise TypeError('Ошибка в типе ответа API')
    if 'homeworks' not in response or 'current_date' not in response:
        raise exceptions.EmptyResponseFromAPI('Пустой ответ от API')
    homeworks = response.get('homeworks')
    if not isinstance(homeworks, list):
        raise TypeError('homeworks не является списком')
    homeworks = response.get('current_date')
    if not isinstance(homeworks, int):
        raise TypeError('current_date не является целым числом')
    return homeworks


def parse_status(homework):
    """Извлекаем статус работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе отсутсвует ключ homework_name')
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise exceptions.UndocumentedStatusError(
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
        logging.critical('Отсутствуют переменные окружения')
        sys.exit('Отсутствуют переменные окружения')
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
            logging.error(f'Сбой в работе бота: {error}')
            message = f'Сбой в работе бота: {error}'
            send_message(bot, message)
        finally:
            logging.info('Ждем 10 минут и проверяем статус')
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        filename='bot.log',
        filemode='w',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    logger = logging.getLogger(__name__)
    logger.addHandler(
        logging.StreamHandler(stream=sys.stdout,)
    )
    main()
