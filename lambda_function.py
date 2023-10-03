import logging
from collections import defaultdict
import os
from datetime import datetime
import boto3
import json
import uuid
from enum import Enum
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import dateutil.tz

logger = logging.getLogger()
logger.setLevel(logging.INFO)


class URLS(Enum):
    ADD_ITEMS = '/add-items'
    DELETE_ITEM = '/delete-item'
    GET_ITEMS = '/get-items'
    SEND_MAIL = '/send-mail'
    UPDATE_ITEM = '/update-item'


def create_response(res, status_code=200):
    https_res = {'isBase64Encoded': False, 'statusCode': status_code, 'headers': {}}
    https_res['headers']['Content-Type'] = 'application/json'
    https_res['body'] = str(json.dumps(res)) if status_code == 200 else str(json.dumps(res.__repr__()))
    logger.info(https_res)
    return https_res


def lambda_handler(event, context=None):
    try:
        logger.info(event)
        if event['path'] == URLS.ADD_ITEMS.value:
            items = json.loads(event['body'])['items']
            for item in items:
                logger.info(f'working on item:{item}')
                add_items_to_db(item['email'], item['date'], item['message'])
            return create_response({'msg': 'insertion done'})

        elif event['path'] == URLS.DELETE_ITEM.value:
            id_to_delete = json.loads(event['body'])['uuid']
            delete_item_from_db(id_to_delete)
            return create_response({'msg': 'deletion done'})

        elif event['path'] == URLS.GET_ITEMS.value:
            email_id = json.loads(event['body'])['email_id']
            items = get_items_from_db(email_id)
            return create_response({'msg': items})

        elif event['path'] == URLS.UPDATE_ITEM.value:
            item = json.loads(event['body'])['item']
            add_items_to_db(item['email'], item['date'], item['message'], item['uuid'])
            return create_response({'msg': 'update done'})

        elif event['path'] == URLS.SEND_MAIL.value:
            generate_mail()
            return create_response({'msg': 'mail sent'})


    except Exception as e:
        logger.error(f'error:{e}')
        create_response(res=e, status_code=500)


def get_db():
    db = boto3.resource('dynamodb')
    table_name = 'email-table'
    table = db.Table(table_name)
    return table


def get_items_from_db(email_id):
    try:
        table = get_db()
        response = table.scan(
            FilterExpression='email_id = :email_id',
            ExpressionAttributeValues={
                ':email_id': email_id
            }
        )
        logger.info(f'item with {id} deleted')
        return {'data': response['Items'], 'count': response['Count']}
    except Exception as e:
        logger.error(f'Get operation failed for dynamodb {id}')
        raise Exception(f'get failed {e}')


def delete_item_from_db(id):
    try:
        table = get_db()
        table.delete_item(Key={'uuid': id})
        logger.info(f'item with {id} deleted')
    except Exception as e:
        logger.error(f'Delete operation failed for dynamodb {id}')
        raise Exception(f'Insert failed {e}')


def add_items_to_db(email, date, message, update_id=None):
    try:
        table = get_db()
        new_id = str(uuid.uuid4()) if not update_id else update_id
        table.put_item(Item={'uuid': new_id, 'email_id': email, 'date_to_publish': date, 'message': message})
        logger.info(f'item inserted for {email} {date} {message}')
    except Exception as e:
        logger.error(f'Insert operation failed for dynamodb {email},{message},{date}')
        raise Exception(f'Insert failed {e}')


def generate_mail():
    try:
        table = get_db()
        response = table.scan()
        logger.info(f'response: {response}')
        message_to_send = defaultdict(list)
        ist_timezone = dateutil.tz.gettz('Asia/Kolkata')
        current_datetime_ist = datetime.now(ist_timezone)
        for item in response['Items']:
            if item['date_to_publish'] == current_datetime_ist.strftime('%d/%m/%Y'):
                message_to_send[item['email_id']].append(item['message'])
                delete_item_from_db(item['uuid'])
        print(message_to_send)
        for email, messages in message_to_send.items():
            to_email = email
            count = len(messages)
            subject = f'[Your Tasks For Today] You have {count} tasks that require your attention.'
            body = generate_html_body(messages)
            send_email(subject=subject, to_email=to_email, body=body)
    except Exception as e:
        logger.error(f'Could not generate body for requested email {e}')
        raise Exception(f'Mail body generation failed {e}')


def generate_html_body(messages):
    body = ''
    body += ''.join([f'<li>{message}</li>' for message in messages])
    email_template = f"""
    <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body>
            Life is like riding a bicycle. To keep your balance, you must keep moving." —Albert Einstein
            <br>  
            Your tasks for Today:
            <br>
            <ul>  
            {body}
            </ul>
            <br>
            Have a great day! (^_^)  
        </body>
        </html>
    """
    return email_template


def send_email(subject, to_email, body):
    try:
        sender_email = 'tasksdaily4you@gmail.com'
        password = os.environ['EMAIL_PASSWORD']
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        msg['Subject'] = subject

        msg.attach(MIMEText(body, 'html'))

        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, password)

            server.sendmail(sender_email, to_email, msg.as_string())
        logger.info(f"Email sent successfully to {to_email}")
    except Exception as e:
        logger.error(f'Email for user {to_email} could not be sent error: {e}')
        raise Exception(f'Email failed {e}')


# if __name__ == '__main__':
    # val = lambda_handler({"path": '/add-items', "body":
    #     """{"items": [{"date":"10/1/23", "email":"ad747300@gmail.com", "message":"remind me to buy milk"},
    #     {"date":"10/1/24", "email":"ad747300@gmail.com", "message":"remind me to sell cheese"}]}"""})
    # val = lambda_handler({"path": '/delete-item', "body":
    #     """{"uuid":"2d545938-714a-4e57-aed1-bb7498684674"}"""})
    # val = lambda_handler({"path": '/get-items', "body": """{"email_id":"ad747300@gmail.com"}"""})
    # val = lambda_handler({"path": '/update-item', "body":
    #     """{"item":{"date":"10/1/23", "email":"ad747300@gmail.com", "message":"remind me to buy milky milk",
    #     "uuid":"3fcd8903-c488-4ea2-940c-7da5352bf343"}}"""})
    # val = lambda_handler({"path": '/send-mail'})
