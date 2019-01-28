from typing import MutableMapping, Any, Optional, List, Tuple
from django.conf import settings

import re
import json

from zerver.models import SubMessage


def get_widget_data(content: str) -> Tuple[Optional[str], Optional[str]]:
    valid_widget_types = ['tictactoe', 'poll', 'todo']
    tokens = content.split(' ')

    # tokens[0] will always exist
    if tokens[0].startswith('/'):
        widget_type = tokens[0][1:]
        if widget_type in valid_widget_types:
            remaining_content = content.replace(tokens[0], '', 1).strip()
            extra_data = get_extra_data_from_widget_type(remaining_content, widget_type)
            return widget_type, extra_data

    return None, None

def get_extra_data_from_widget_type(content: str,
                                    widget_type: Optional[str]) -> Any:
    if widget_type == 'poll':
        # This is used to extract the question from the poll command.
        # The command '/poll question' will pre-set the question in the poll
        lines = content.splitlines()
        question = ''
        options = []
        if lines and lines[0]:
            question = lines.pop(0).strip()
        for line in lines:
            # If someone is using the list syntax, we remove it
            # before adding an option.
            option = re.sub(r'(\s*[-*]?\s*)', '', line.strip())
            if len(option) > 0:
                options.append(option)
        extra_data = {
            'question': question,
            'options': options,
        }
        return extra_data
    return None

def do_widget_post_save_actions(message: MutableMapping[str, Any]) -> None:
    '''
    This is experimental code that only works with the
    webapp for now.
    '''
    if not settings.ALLOW_SUB_MESSAGES:
        return
    content = message['message'].content
    sender_id = message['message'].sender_id
    message_id = message['message'].id

    widget_type = None
    extra_data = None

    widget_type, extra_data = get_widget_data(content)
    widget_content = message.get('widget_content')
    if widget_content is not None:
        # Note that we validate this data in check_message,
        # so we can trust it here.
        widget_type = widget_content['widget_type']
        extra_data = widget_content['extra_data']

    if widget_type:
        content = dict(
            widget_type=widget_type,
            extra_data=extra_data
        )
        submessage = SubMessage(
            sender_id=sender_id,
            message_id=message_id,
            msg_type='widget',
            content=json.dumps(content),
        )
        submessage.save()
        message['submessages'] = SubMessage.get_raw_db_rows([message_id])
