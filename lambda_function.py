# -*- coding: utf-8 -*-

# This is the Le mie scadenze Alexa Skill

import logging

from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.utils import is_request_type, is_intent_name
from ask_sdk_core.handler_input import HandlerInput
from ask_sdk_model import Response
from ask_sdk_model import IntentConfirmationStatus
from ask_sdk_model.ui import SimpleCard
from ask_sdk_model.ui import AskForPermissionsConsentCard
#from ask_sdk_core.api_client import DefaultApiClient
from ask_sdk_model.services.reminder_management import (
    ReminderRequest, Trigger, TriggerType, AlertInfo, PushNotification,
    PushNotificationStatus, ReminderResponse, SpokenInfo, SpokenText)
#added from test_attributes_manager.py
from ask_sdk.standard import  StandardSkillBuilder
from ask_sdk_model.request_envelope import RequestEnvelope
from ask_sdk_model.session import Session
from ask_sdk_core.attributes_manager import (
    AttributesManager, AttributesManagerException)
from ask_sdk_model.services import ServiceException

from partition_keygen import user_id_partition_keygen

from datetime import date, datetime

skill_name = "Le mie scadenze"
help_text = ("Ciao. Puoi dire: aggiungi latte con scadenza 5 Agosto")

sample_saved_attributes = {'4': {'expiration': '2019-08-03', 'object': 'latte'}, 
                           '5': {'expiration': '2019-08-04', 'object': 'vino'}, 
                           '3': {'expiration': '2019-08-05', 'object': 'acqua'}}

import boto3
dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
#dynamodb = boto3.client('dynamodb', region_name='eu-west-1')

sb = StandardSkillBuilder(table_name="Scadenze",
		auto_create_table=True,
		partition_keygen=user_id_partition_keygen, 
		dynamodb_client=dynamodb)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

welcome_speech =  {
		"en-US": "Welcome. You can say: Add milk with expiration August 5th",
		"it-IT": "Ciao. Puoi dire: aggiungi latte con scadenza 5 Agosto."
		}
FOOD_SLOT = "food"
DATE_SLOT = "date"
NOTIFY_MISSING_PERMISSIONS = ("Please enable Reminders permissions in "
                              "the Amazon Alexa app.")


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
#    attr = handler_input.attributes_manager.session_attributes
    slots = handler_input.request_envelope.request.intent.slots
    food = slots[FOOD_SLOT].value
    date = slots[DATE_SLOT].value
    attributesManager = handler_input.attributes_manager
    newdata = {
            "object": food,
            "expiration": date
              }
    logger.info("Before getting persistent attributes")
    try:
        saved_attr = attributesManager.persistent_attributes
        logger.info(saved_attr)
        if saved_attr == {}:
            newid = "1"
        else:
            maxid = max(saved_attr.keys())
            newid = str(int(maxid) + 1)
    except AttributesManagerException:
        logger.info("Persistent Adapter is not defined")
    except:
        newid = "1"
    logger.info("After getting persistent attributes")
    logger.info(newid)
#TODO clean expired entries before saving
#TODO develop an Interceptor to cache data
#TODO Lettere accentate
    newpersdata =  { newid: newdata }
    logger.info("Newpersdata=")
    logger.info(newpersdata)
    pers_attr = { **saved_attr, **newpersdata }
    attributesManager.persistent_attributes = pers_attr
    logger.info("Added Newpersdata to existing persistent attributes")
    attributesManager.save_persistent_attributes()
#TODO set a reminder
    #check permissions for the Reminder
    permissions = ["alexa::alerts:reminders:skill:readwrite"]
    req_envelope = handler_input.request_envelope
    response_builder = handler_input.response_builder
    # Check if user gave permissions to create reminders.
    # If not, request to provide permissions to the skill.
    if not (req_envelope.context.system.user.permissions and
            req_envelope.context.system.user.permissions.consent_token):
        response_builder.speak(NOTIFY_MISSING_PERMISSIONS)
        response_builder.set_card(
            AskForPermissionsConsentCard(permissions=permissions))
        return response_builder.response


    #build alert and trigger for the Reminder Request
    reminder_date = datetime.strptime(date, "%Y-%m-%d")
    reminder_date = reminder_date.replace(hour=13, minute=0)
#TODO manage locale language
    text = SpokenText(locale=None, ssml=None, text='Per favore, autorizza i promemoria')
    alert = AlertInfo(spoken_info=SpokenInfo([text]))
    trigger = Trigger(object_type=TriggerType.SCHEDULED_ABSOLUTE, 
                      scheduled_time=reminder_date,
                      offset_in_seconds=None, 
                      time_zone_id=None, 
                      recurrence=None)
    reminder_request = ReminderRequest(request_time=datetime.now(),
                                       trigger=trigger, 
                                       alert_info=alert, 
                                       push_notification=PushNotification(PushNotificationStatus.ENABLED)
                                       )
    api_client = handler_input.service_client_factory.get_reminder_management_service()
    #Create Reminder
    try:
        response = api_client.create_reminder(reminder_request)
        speech = "Ho messo un promemoria alle ore tredici della data di scadenza."
        logger.info(f"Created reminder : {response}")
        return handler_input.response_builder.speak(speech).set_card(
            SimpleCard(
                "Reminder created with id", response.alert_token)).response
    except ServiceException as e:
        logger.info("Exception encountered : {}".format(e.body))
        speech_text = "Uh Oh. Looks like something went wrong."
        return handler_input.response_builder.speak(speech_text).set_card(
            SimpleCard(
                "Reminder not created",str(e.body))).response
#TODO review after new code for Reminder
    speech = "Aggiungo " + food + " con data di scadenza " + date
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("listExpirations"))
def listExpirationsIntent_handler(handler_input):
    """Elenca gli oggetti in lista con relativa data di scadenza
    """
    # type: (HandlerInput) -> Response
    logger.info("In listExpirations")
    attributesManager = handler_input.attributes_manager
    try:
        saved_attr = attributesManager.persistent_attributes
    except AttributesManagerException:
        logger.info("Persistent Adapter is not defined")
    logger.info("After getting persistent attributes")
    if saved_attr == {}:
        speech = "La lista e' vuota."
    else:
        speech=""
        for k in saved_attr.keys():
            speech += saved_attr[k]['object']+" scadra' il giorno "+saved_attr[k]['expiration']+". "
            
#    speech = "Quando sara' pronta elenchera gli oggetti in lista con relativa data di scadenza"
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("deleteExpirations"))
def deleteExpirationsIntent_handler(handler_input):
    """Cancella tutti gli oggetti nella lista di scadenza se l'utente conferma.
    """
    # type: (HandlerInput) -> Response
    logger.info("In deleteExpirations")
    confirmationStatus = handler_input.request_envelope.request.intent.confirmation_status
    logger.info(confirmationStatus)
#    confirmationStatus = intent["confirmationStatus"]
    if confirmationStatus == IntentConfirmationStatus.DENIED:
        speech = "OK, non cancello nulla"
    else:
        handler_input.attributes_manager.delete_persistent_attributes()
        speech = "Ho cancellato tutte le scadenze in lista"
    handler_input.response_builder.set_should_end_session(True)
    handler_input.response_builder.speak(speech)
    return handler_input.response_builder.response

@sb.request_handler(can_handle_func=is_intent_name("nextExpiration"))
def nextExpirationIntent_handler(handler_input):
    """Comunica l'oggetto di piu prossima scadenza                 
    """
    # type: (HandlerInput) -> Response
    logger.info("In nextExpiration")
    attributesManager = handler_input.attributes_manager
    try:
        saved_attr = attributesManager.persistent_attributes
    except AttributesManagerException:
        logger.info("Persistent Adapter is not defined")
    logger.info(saved_attr)
    if saved_attr == {}:
        speech = "Lista vuota."
    else:
        today = date.today().isoformat()
        next_expiration = '2999-01-01'
        next_object = ''
        for k in saved_attr.keys():
            expir = saved_attr[k]['expiration']
            if  expir >= today and expir < next_expiration:
                next_expiration = expir
                next_object = saved_attr[k]['object']
        if next_object == '':
            speech = "Nessuna scadenza nel futuro."
        else:
            speech = next_object+" scadra' il giorno "+next_expiration+". "
    
#    speech = "Quando sara pronta comunichera l'oggetto di prossima scadenza"
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
