import tempfile
from random import random, randint

from flask import request, json
from werkzeug.utils import secure_filename

from .app import app
from .controllerutils import buildSearchResponseJSON, sequenceInfoFromObjects
from .dataformats import SearchResponse
from .parser import parse
from Pinger.Pinger import *


@app.route('/ping')
def hello_world():
    return 'pong'


@app.route('/vendors')
def get_vendors():
    return json.jsonify({'vendors': ['Twist', 'IDT', 'GenA']})


@app.route('/upload', methods=['post'])
def uploadFile():
    if 'seqfile' not in request.files or request.files['seqfile'] == "":
        return json.jsonify({'error': 'No file specified'})

    resp = SearchResponse()
    for i in range(0, 10):
        vendor_id = randint(0, 1)
        resp.result[0]['offers'].append({
            "vendorinformation": {
                "name": "Twist DNA ..." if vendor_id == 0 else "IDT DNA ...",
                "shortname": "Twist" if vendor_id == 0 else "IDT",
                "key": ""
            },
            "price": random(),
            "turnovertime": randint(1, 20)
        })


    # Store the input in a temporary file for the parser to process
    tempf, tpath = tempfile.mkstemp('.' + secure_filename(request.files['seqfile'].filename).rsplit('.', 1)[1].lower())
    request.files['seqfile'].save(tpath)

    mainPinger = CompositePinger()

    # Begin temporary testing placeholders
    dummyVendor = VendorInformation()
    dummyPinger = DummyPinger()
    mainPinger.registerVendor(dummyVendor, dummyPinger)
    mainPinger.registerVendor(dummyVendor, dummyPinger)
    mainPinger.registerVendor(dummyVendor, dummyPinger)
    mainPinger.registerVendor(dummyVendor, dummyPinger)
    # End temporary testing placeholders

    try:
        # Parse sequence file
        objSequences = parse(tpath)

        # Adapt SeqObject to SequenceInformation
        sequences = sequenceInfoFromObjects(objSequences)

        # Search and retrieve offers for each sequence
        mainPinger.searchOffers(sequences)
        seqoffers = mainPinger.getOffers()

        return buildSearchResponseJSON(seqoffers)


    except NameError:
        return json.jsonify({'error': 'File format not supported'})

