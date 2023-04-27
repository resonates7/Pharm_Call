import json
from re import A
import google.cloud.dlp
from google.cloud import storage
from io import BytesIO

input_bucket_name = 'transcript_landing'
out_bucket_name = 'redacted_transcript_landing'
prefix = "gs://"

info_types = [
    "PERSON_NAME",
    "URL",
    "PHONE_NUMBER",
    "FIRST_NAME",
    "LAST_NAME",
    "EMAIL_ADDRESS",
    "DATE_OF_BIRTH",
    "EMAIL_ADDRESS",
    "US_SOCIAL_SECURITY_NUMBER",
    "STREET_ADDRESS",
    "FEMALE_NAME", 
    "US_DRIVERS_LICENSE_NUMBER", 
    "MALE_NAME", 
    "LAST_NAME", 
    "US_SOCIAL_SECURITY_NUMBER", 
    "US_INDIVIDUAL_TAXPAYER_IDENTIFICATION_NUMBER", 
    "FIRST_NAME", 
    "STREET_ADDRESS"
]


def deidentify_with_replace(
    project,
    input_str,
    info_types,
    replacement_str="###",
):
    """Uses the Data Loss Prevention API to redact personal identification information from
        call transcripts.
    Args:
        project: The Google Cloud project id to use as a parent resource.
        input_str: The string to deidentify (will be treated as text).
        info_types: A list of strings representing info types to look for.
        replacement_str: The string to replace all values that match given
            info types.
    Returns:
        None; the response is loaded to the cloud storage out bucket.
    """
    # create a storage client to access unredacted transcripts stored on the input bucket
    storage_client = storage.Client()
    bucket = storage_client.bucket(input_bucket_name)
    blob = bucket.blob(input_str)
    gcs_uri = prefix + input_bucket_name + "/" + blob.name
    print(gcs_uri)
 
 
    # Instantiate a google cloud data loss prevention client to effect the redactions
    dlp = google.cloud.dlp_v2.DlpServiceClient()

    # Convert the project id into a full resource id.
    parent = f"projects/{project}"

    # Construct inspect configuration dictionary to instruct what to react
    inspect_config = {"info_types": [{"name": info_type} for info_type in info_types]}

    # Construct deidentify configuration dictionary
    deidentify_config = {
        "info_type_transformations": {
            "transformations": [
                {
                    "primitive_transformation": {
                        "replace_config": {
                            "new_value": {"string_value": replacement_str}
                        }
                    }
                }
            ]
        }
    }

    # construct input to redaction as text
    # a = blob.download_as_string()
    # print('download as string', a)
    item = {"value": blob.download_as_string()}
    #print(item)


    # Call the API
    response = dlp.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "inspect_config": inspect_config,
            "item": item,
        }
    )


    #transcripts_json = type(response).to_json(response)
    #move transcript to landing bucket
    print('redaction complete, loading bucket with redacted transcript')
    storage_client = storage.Client()
    bucket = storage_client.bucket(out_bucket_name)
    blob = bucket.blob(blob.name)
    blob.upload_from_string(response.item.value)


def hello_gcs(event, context):
    """Background Cloud Function to be triggered by Cloud Storage.
       This generic function logs relevant data when a file is changed,
       and works for all Cloud Storage CRUD operations.
    Args:
        event (dict):  The dictionary with data specific to this type of event.
                       The `data` field contains a description of the event in
                       the Cloud Storage `object` format described here:
                       https://cloud.google.com/storage/docs/json_api/v1/objects#resource
        context (google.cloud.functions.Context): Metadata of triggering event.
    Returns:
        None; the output is written to Cloud Logging
    """

    print('Event ID: {}'.format(context.event_id))
    print('Event type: {}'.format(context.event_type))
    print('Bucket: {}'.format(event['bucket']))
    print('File: {}'.format(event['name']))
    print('Metageneration: {}'.format(event['metageneration']))
    print('Created: {}'.format(event['timeCreated']))
    print('Updated: {}'.format(event['updated']))


    deidentify_with_replace("gsk-grc", event['name'], info_types, replacement_str="[##redacted##]")