import json
import re
from datetime import datetime
import requests
from .Pinger import *
from .Validator import *

class GeneArtClient: 
    # Constructur for a GeneArtClient ()
    # Takes as input the configuration's parameters 
    # dnaStrings and hqDnaStrings have per defualt the value True

    def __init__(self, server, validate, status, addToCart, upload, username, token, dnaStrings = True, hqDnaStrings = True, timeout = 60): 
        self.server = server
        self.validate = validate
        self.status = status
        self.addToCart = addToCart
        self.upload = upload
        self.username = username
        self.token = token
        self.dnaStrings = dnaStrings 
        self.hqDnaStrings = hqDnaStrings
        self.timeout = timeout
        self.validAcc = self.authenticate()
        if(self.validAcc == False):
            raise AuthenticationError('User Credentials are wrong')
        
    # Defines the destination address for the action defined in the parameter     
    def destination(self, action):
        if(action == "validate"):
            return self.server + self.validate
        if(action == "status"):
            return self.server + self.status
        if(action == "addToCart"):
            return self.server + self.addToCart
        if(action == "upload"):
            return self.server + self.upload
    
    # Returns the authentication field which is used in several requests.
    def getAuthPart(self, projectId):
        request = {
            "authentication":
         { "username": self.username,
           "token": self.token
         }, 
         "projectId": projectId
        }
        return request
    
    # Authentication Operation
    # Checks if the username and password are correct
    # Distinguishes based on the error message
    def authenticate(self):
        result = self.statusReview("2019AAAAAX") # Dummy projectId
        if("errortype" in result.keys() and result["errortype"] == "authenticationFailed"):
            return False
        else:
            return True

    # Review stored project
    def statusReview(self, projectId):
        request = self.getAuthPart(projectId)
        dest = self.destination("status")
        resp = requests.post(dest, json = request, timeout = self.timeout)
        result = resp.json()
        return result

    # Add Project to Cart
    def toCart(self, projectId):
        request = self.getAuthPart(projectId)
        dest = self.destination("addToCart")
        resp = requests.post(dest, json = request, timeout = self.timeout)
        result = resp.json()
        return result
    
    # Upload Project with constructs
    def constUpload(self, listOfSequences, product):
        now = datetime.now() 
        dt_string = now.strftime("%d-%m-%Y_%H_%M")
        projectname = "ect-" + str(dt_string)
        dest = self.destination("upload")
        constructsList = []
        for construct in listOfSequences:
            sequence = {
                "name": self.generateName(construct["name"]),
                "sequence": construct["sequence"],
                "product": product,
                "comment": "idN: " + construct["idN"] + " , name: " + construct["name"]
              }
            constructsList.append(sequence)
        request = {
            "authentication":
         { "username": self.username,
           "token": self.token
         },
            "project": {
                "name": projectname,
                "constructs": constructsList
            }
        }
        resp = requests.post(dest, json = request, timeout = self.timeout)
        result = resp.json()
        return result
    
    # Validate Project
    def projectValidate(self, listOfSequences, product):
        now = datetime.now() 
        dt_string = now.strftime("%d-%m-%Y_%H_%M")
        projectname = "project-" + str(dt_string)
        dest = self.destination("validate")
        constructsList = []
        for construct in listOfSequences:
            sequence = {
                "name": self.generateName(construct["name"]),
                "sequence": construct["sequence"],
                "product": product,
                "comment": "idN: " + construct["idN"] + " , name: " + construct["name"]
              }
            constructsList.append(sequence)
        request = {
           "project": {
                "name": projectname,
                "constructs": constructsList
            }
        }
        resp = requests.post(dest, json = request, timeout = self.timeout)
        result = resp.json()
        return result
    
    # Name-Generator used to define project name if none is given and adjust the given name if it isn't conform the documentation
    def generateName(self, prevName):
        if(len(prevName) == 0):
            now = datetime.now() 
            dt_string = now.strftime("%d/%m/%Y_%H:%M")
            prevName = "consname-" + str(dt_string)
        else: 
            if(len(prevName) > 20):
                prevName = prevName[:20]
        clean_consName = re.sub(r'[^.A-z0-9_\-]', "_", prevName)
        return clean_consName


#
#   The GeneArt Pinger
#
class GeneArt(BasePinger):
    # The configuration's parameters 
    # dnaStrings and hqDnaStrings have per defualt the value True

    server_default = "https://www.thermofisher.com/order/gene-design-ordering/api"
    validate_default = "/validate/v1"
    status_default = "/status/v1"
    addToCart_default = "/addtocart/v1"
    upload_default = "/upload/v1"
    dnaStrings_default = True
    hqDnaStrings_default = True
    timeout_default = 60
    
    #
    # Constructur for a GeneArt-Pinger
    # Takes as input the log-in parameters.
    #
    def __init__(self, username, token, server = server_default, validate = validate_default, status = status_default, addToCart = addToCart_default, upload = upload_default, dnaStrings = dnaStrings_default, hqDnaStrings = hqDnaStrings_default, timeout = timeout_default):
        self.running = False

        self.server = server
        self.validate = validate
        self.status = status
        self.addToCart = addToCart
        self.upload = upload
        self.username = username
        self.token = token
        self.dnaStrings = dnaStrings 
        self.hqDnaStrings = hqDnaStrings
        self.timeout = timeout
       
        try:
            self.client = GeneArtClient(self.server, 
                      self.validate, self.status, self.addToCart,
                      self.upload, 
                      self.username, self.token, 
                      self.dnaStrings, self.hqDnaStrings, self.timeout)
        except requests.exceptions.RequestException as err:
            raise UnavailableError("Request got timeout") from err


        self.offers = []
        self.products = {"815010DE": 89.00,"815020DE": 109.00, "815030DE": 119.00, "815040DE": 182.00}
        self.validator = EntityValidator(raiseError=True)
    

    #
    #   Encodes a 'SequenceInformation' object into JSON-Format with fields readable by the GeneArtClient.
    #       Returns the newly created object, if the given input is valid. Otherwise raises a 'TypeError'
    #
    def encode_sequence(self, seqInf):
        if isinstance(seqInf, SequenceInformation):
            if self.validator.validate(seqInf):
                return { "idN": seqInf.key, "name": seqInf.name, "sequence": seqInf.sequence}
        else:
            type_name = seqInf.__class__.__name__
            raise InvalidInputError(f"Parameter must be of type SequenceInformation but is of type '{type_name}'.")
    
    #
    #   Authenticates the instance
    #       Returns True if the authentication was successful and False otherwise.
    #
    def authenticate(self):

        # Authenticate by calling the corresponding method.
        response = {}
        try:
            response = self.client.authenticate()
        except requests.exceptions.RequestException as err:
            raise UnavailableError("Request got timeout") from err
        except:
            messageText = 'Wrong Credentials'
            return Message(MessageType.WRONG_CREDENTIALS, messageText)
        else:
            return response
        
    #
    #   After:
    #       isRunning() -> true
    #       getOffers() -> [SequenceOffer(seqInf[0], self.tempOffer), SequenceOffer(seqInf[1], self.tempOffer), ...
    #                           SequenceOffer(seqInf[n], self.tempOffer)]
    #
    def searchOffers(self, seqInf):

        # Check pinger is not running
        if(self.isRunning()):
            raise IsRunningError("Pinger is currently running and can not perform a other action")
        
        try: 
            self.running = True
            offers = [] # Empty Offers List
            for product in "dnaStrings", "hqDnaStrings": # Two possible Product Types. 
                try:
                    response = self.projectValidate(seqInf, product)
                except requests.exceptions.RequestException as err:  # If request timeout             
                    self.running = False
                    raise UnavailableError from err
    
                count = 0 # Count the sequences
                for seq in seqInf:
                    accepted = response["constructs"][count]["accepted"] # See if the API accepted the sequence
                    if accepted == True:
                        messageText = product + "_" + "accepted"
                        message = Message(MessageType.INFO, messageText)
                        turnOverTime = response["constructs"][count]["eComInfo"]["productionDaysEstimated"]
                        productCode = response["constructs"][count]["eComInfo"]["lineItems"][0]["sku"]
                        if(productCode in list(self.products.keys())):
                            price = Price(amount = self.products[productCode], customerSpecific=True)
                        else:
                            price = Price()
                    else:
                        turnOverTime = -1
                        price = Price()
                        if(len(response["constructs"][count]["reasons"]) == 1):
                            reason = response["constructs"][count]["reasons"][0]
                            if (reason == "length"):
                                messageText = product + "_" + "rejected_" + str(reason) + "."
                                message = Message(MessageType.INVALID_LENGTH, messageText)
                            if (reason == "homology"):
                                messageText = product + "_" + "rejected_" + str(reason) + "."
                                message = Message(MessageType.HOMOLOGY, messageText)
                            if (reason == "problems"):
                                messageText = product + "_" + "rejected_" + str(reason) + "."
                                message = Message(MessageType.INVALID_LENGTH, messageText)
                        else:
                            messageText = product + "_" + "rejected_"
                            for reason in response["constructs"][count]["reasons"]:
                                messageText = messageText + str(reason) + "."
                            message = Message(MessageType.SYNTHESIS_ERROR, messageText)
    
                    seqOffer = SequenceOffers(seq, [Offer(price = price, turnovertime = turnOverTime, messages = [message])])
                    offers.append(seqOffer)
                    count = count + 1
            self.offers = offers
            self.running = False
        except InvalidInputError as err:
            self.running = False
            raise InvalidInputError from err
        except requests.exceptions.RequestException as err:
            raise UnavailableError("Request got a error") from err
        except UnavailableError as err:
            self.running = False
            raise UnavailableError from err
        except Exception as err:
            self.running = False
            raise UnavailableError from err    
        
    
    # 
    #   Upload Project with constructs
    #       Takes as input a list of 'SequenceInformation' objects and the desired product type 
    #           (The parameter "product" can only have the value: 'dnaStrings' or 'hqDnaStrings')
    #       Returns the API-Response 
    # 
    def constUpload(self, seqInf, product):
        # Sequences in JSON-Format with fields readable by the GeneArtClient. At first is empty.
        gaSequences  = []
        for s in seqInf:
            # Encode each element in JSON-Format with fields readable by the GeneArtClient and add it to the list.
            seq = self.encode_sequence(s)
            gaSequences.append(seq)
        # Upload the construct by calling the corresponding method.
        response = self.client.constUpload(gaSequences, product)
        return response
    
    #    
    #   Validate Project
    #       Takes as input a list of 'SequenceInformation' objects and the desired product type 
    #           (The parameter "product" can only have the value: 'dnaStrings' or 'hqDnaStrings')
    #       Returns the API-Response     
    #
    def projectValidate(self, seqInf, product):
        # Sequences in JSON-Format with fields readable by the GeneArtClient. At first is empty.
        gaSequences  = []
        for s in seqInf:
            # Encode each element in JSON-Format with fields readable by the GeneArtClient and add it to the list.
            seq = self.encode_sequence(s)
            gaSequences.append(seq)
        # Validate the project by calling the corresponding method.
        response = self.client.projectValidate(gaSequences, product)
        return response
        
    #
    #   Checks if the Pinger is Running.
    #
    def isRunning(self):
        return self.running

    #
    #   Returns List with a  SequenceOffer for every sequence in last searchOffers(seqInf)-call.
    #   Every SequenceOffer contains the same offers. Default 1 see self.tempOffer and self.offers.
    #
    def getOffers(self):
        return self.offers
    
    #
    #   Add to Cart
    #       Takes as parameter a projectId       
    #       Returns the API-Response
    #
    def toCart(self, projectId):
        # Add the project to cart by calling the corresponding method.
        try:
            response = self.client.toCart(projectId)
        except requests.exceptions.RequestException as err:
            raise UnavailableError("Request got Timeout") from err

        return response
        
    #
    #   Status Review
    #       Takes as parameter a projectId       
    #       Returns the API-Response
    #
    def statusReview(self, projectId):
        # Review the status of the project by calling the corresponding method.
        try:
            response = self.client.statusReview(projectId)
        except requests.exceptions.RequestException as err:
            raise UnavailableError("Request got timeout") from err

        return response
    #
    #   Desc:   Resets the pinger by
    #               - stop searching -> isRunning() = false
    #               - resets the offers to a empty list -> getOffers = []
    #
    def clear(self):
        self.running = False
        self.offers = [] # Empty Offers List


    #
    #   Desc:   Create a request to trigger an order.
    #
    #   @param seqInf
    #           Type ArrayOf(Entities.SequenceInformation). Representation of the sequences you want to order.
    #
    #   @result
    #           Type Entities.Order. Representation of the order.
    #
    def order(self, seqInf):
        self.running = True
        constructUpload = self.constUpload(seqInf, "dnaStrings")
        if(len(constructUpload["project"]["constructs"]) != len(seqInf)):
            messageText = "The selected sequences cannot be synthesised."
            message = Message(MessageType.SYNTHESIS_ERROR, messageText)
            return message            
            self.running = False
        else:
            projectId = constructUpload["project"]["projectId"]
            toCartResponse = self.toCart(projectId)
            expectedKeys = ["projectId", "cartId"]
            if(expectedKeys == list(toCartResponse.keys())):
                messageText = "Project: " + str(toCartResponse["projectId"]) + "has been successfully added to cart: " + str(toCartResponse["cartId"])
                message = Message(MessageType.INFO, messageText)
            else:
                messageText = "Unable to order sequences at the moment."
                message = Message(MessageType.API_CURRENTLY_UNAVAILABLE, messageText)
        return message
        self.running = False