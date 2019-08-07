# -*- coding: utf-8 -*-

# This is the Le mie scadenze Alexa Skill

import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model.ui import SimpleCard
#added from test_attributes_manager.py
from ask_sdk.standard import  StandardSkillBuilder
from ask_sdk_model.request_envelope import RequestEnvelope
from ask_sdk_model.session import Session
from ask_sdk_core.attributes_manager import (
    AttributesManager, AttributesManagerException)

skill_name = "Le mie scadenze"
help_text = ("Ciao. Puoi dire: aggiungi latte con scadenza 5 Agosto")

sb = StandardSkillBuilder()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

welcome_speech =  {
		"en-US": "Welcome. You can say: Add milk with expiration August 5th",
		"it-IT": "Ciao. Puoi dire: aggiungi latte con scadenza 5 Agosto."
		}
FOOD_SLOT = "food"
DATE_SLOT = "date"

@sb.request_handler(can_handle_func=is_request_type("LaunchRequest"))
def launch_request_handler(handler_input):
    """Handler for Skill Launch."""
    # type: (HandlerInput) -> Response
    logger.info("In LaunchRequestHandler")

    lang = handler_input.request_envelope.request.locale
    try:
        speech = welcome_speech[lang]
    except:
        speech = "Language " + lang + " is not supported."

    handler_input.response_builder.speak(
        speech).ask(help_text)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.HelpIntent"))
def help_intent_handler(handler_input):
    """Handler for Help Intent."""
    # type: (HandlerInput) -> Response
    handler_input.response_builder.speak(help_text).ask(help_text)
    return handler_input.response_builder.response


@sb.request_handler(
    can_handle_func=lambda handler_input:
        is_intent_name("AMAZON.CancelIntent")(handler_input) or
        is_intent_name("AMAZON.StopIntent")(handler_input))
def cancel_and_stop_intent_handler(handler_input):
    """Single handler for Cancel and Stop Intent."""
    # type: (HandlerInput) -> Response
    speech_text = "Goodbye!"

    return handler_input.response_builder.speak(speech_text).response


@sb.request_handler(can_handle_func=is_request_type("SessionEndedRequest"))
def session_ended_request_handler(handler_input):
    """Handler for Session End."""
    # type: (HandlerInput) -> Response
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AddFoodIntent"))
def AddFoodIntent_handler(handler_input):
    """Aggiungi cibo o altro alle scadenza con una data specifica.
    """
    # type: (HandlerInput) -> Response

    logger.info("In AddFoodIntent")
    attr = handler_input.attributes_manager.session_attributes
    slots = handler_input.request_envelope.request.intent.slots
    food = slots[FOOD_SLOT].value
    date = slots[DATE_SLOT].value
    logger.info(slots)
    speech = "Aggiungo " + food + " con data di scadenza " + date
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("listExpirations"))
def AddFoodIntent_handler(handler_input):
    """Elenca gli oggetti in lista con relativa data di scadenza
    """
    # type: (HandlerInput) -> Response
    logger.info("In listExpirations")
    attr = handler_input.attributes_manager.session_attributes
    logger.info(attr)
    speech = "Quando sara pronta elenchera gli oggetti in lista con relativa data di scadenza"
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("nextExpiration"))
def AddFoodIntent_handler(handler_input):
    """Comunica l'oggetto di piu prossima scadenza                 
    """
    # type: (HandlerInput) -> Response
    logger.info("In nextExpiration")
    attr = handler_input.attributes_manager.session_attributes
    logger.info(attr)
    speech = "Quando sara pronta comunichera l'oggetto di prossima scadenza"
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response


@sb.request_handler(can_handle_func=is_intent_name("AMAZON.FallbackIntent"))
def fallback_handler(handler_input):
    """AMAZON.FallbackIntent is only available in en-US locale.
    This handler will not be triggered except in that locale,
    so it is safe to deploy on any locale.
    """
    # type: (HandlerInput) -> Response
    speech = (
        "The {} skill can't help you with that.  "
        "You can tell me your favorite color by saying, "
        "my favorite color is red").format(skill_name)
    reprompt = ("You can tell me your favorite color by saying, "
                "my favorite color is red")
    handler_input.response_builder.speak(speech).ask(reprompt)
    return handler_input.response_builder.response


def convert_speech_to_text(ssml_speech):
    """convert ssml speech to text, by removing html tags."""
    # type: (str) -> str
    s = SSMLStripper()
    s.feed(ssml_speech)
    return s.get_data()


@sb.global_response_interceptor()
def add_card(handler_input, response):
    """Add a card by translating ssml text to card content."""
    # type: (HandlerInput, Response) -> None
    response.card = SimpleCard(
        title=skill_name,
        content=convert_speech_to_text(response.output_speech.ssml))


@sb.global_response_interceptor()
def log_response(handler_input, response):
    """Log response from alexa service."""
    # type: (HandlerInput, Response) -> None
    print("Alexa Response: {}\n".format(response))


@sb.global_request_interceptor()
def log_request(handler_input):
    """Log request to alexa service."""
    # type: (HandlerInput) -> None
    print("Alexa Request: {}\n".format(handler_input.request_envelope.request))


@sb.exception_handler(can_handle_func=lambda i, e: True)
def all_exception_handler(handler_input, exception):
    """Catch all exception handler, log exception and
    respond with custom message.
    """
    # type: (HandlerInput, Exception) -> None
    print("Encountered following exception: {}".format(exception))

    speech = "Sorry, there was some problem. Please try again!!"
    handler_input.response_builder.speak(speech).ask(speech)

    return handler_input.response_builder.response


######## Convert SSML to Card text ############
# This is for automatic conversion of ssml to text content on simple card
# You can create your own simple cards for each response, if this is not
# what you want to use.

from six import PY2
try:
    from HTMLParser import HTMLParser
except ImportError:
    from html.parser import HTMLParser


class SSMLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.full_str_list = []
        if not PY2:
            self.strict = False
            self.convert_charrefs = True

    def handle_data(self, d):
        self.full_str_list.append(d)

    def get_data(self):
        return ''.join(self.full_str_list)

################################################


# Handler to be provided in lambda console.
lambda_handler = sb.lambda_handler()
