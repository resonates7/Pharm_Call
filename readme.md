# GSK Call Project Data Pipeline
This code creates a Google Cloud Platform (GCP) pipeline to transfer GSK's customer service phone call recordings to the cloud. It then reencodes the audio files in a way that can be read by Google Cloud's speech-to-text API, which creates transcripts of the audio recordings. Finally, it removes PII from the transcripts to comply with GSK's policy. Removal of PII allows for safe analysis of customer's experience with GSK.

The pipeline code uses Google's Data Loss Prevention API to remove Personally Identifiable Information (PII). SDI's data science team also created some additional logic using regex to further scrub PII.

This is the code deployed directly in cloud functions on the Google Cloud Platform project named 'GSK-GRC.' These are cloud functions and are hard to get to run locally.

##### Author:
Rob Eidson, Data Engineer


## Process Flow
#### Google Cloud Storage (GCS) Bucket: mdata_start 
GSK emailed an excel file which was uploaded onto this bucket to kick off the process. The excel file must be saved in TSV (tab seperated values) format.

#### Cloud Function: function-1
This function is triggered by the addition of a file on the mdata_start bucket. It then creates a list of file paths showing the location of the audio recordings on GSK's SFTP server. 

Then, it creates thousands of pub sub-topics for each file path. In effect, this is a form of distributed messaging computation that dramatically increases processing speed. This creates decoupled asynchronous messages that persist until the files are downloaded. GCP will keep trying to download the files until compute power becomes available.

From this point onward, GCP spins up multiple compute instances for each file for the rest of the below functions.

#### Cloud Function: sftp_function
This function picks up messages of file paths published to the 'test' topic from function-1. 

First, it authenticates with GSK's server using credentials securely stored in GCP's Secret Manager app. The pub/sub messages are received and decoded by the hello_pubsub function. Then, it passes the decoded file path to the download2() function.

The download2 function gets the file and uses BytesIO to serialize the data stored in memory for faster processing; then, it uploads the serialized files held in memory and stores them onto the 'audio_landing' bucket.

#### Google Cloud Storage Bucket (GCS): audio_landing
Now that the files are in a Cloud Storage Bucket, they're ready to be processed into text transcripts. The audio files are deleted from this location as they're processed to maintain state.

#### Cloud Function:  recode_audio
This function is triggered as customer service audio file recordings are placed on the audio_landing bucket. 

New files added to the audio_landing bucket create an event that is received by the hello_gcs() function, which passes the GSK audio recording file name to the process_audio function.

This function first re-encodes the audio file recording into a codex that GCP's speech to text api can process. Media data is serialized and then decoded using things called a codex. There are literally tens of thousands of codecs in existence. GSK's phone call recordings are encoded in .WAV file format. However, WAV isn't actually a specific encoding. Rather, it's some sort of catch-all bucket of various possible encodings. This was extremely complicated and took me a long time to figure out.

I was able to get it to work using an application called ffmpeg. This module is poorly documented. But, as I recall, its actually some sort of application, but can be instantiated in python. It is included as a system package in Cloud Function’s base image. Here are some documentation links: 

https://ffmpeg.org/ffmpeg.html

https://cloud.google.com/speech-to-text/docs/optimizing-audio-files-for-speech-to-text

https://cloud.google.com/functions/docs/reference/system-packages#ubuntu_1804

Once the audio files have been encoded in a way understandable to GCP's speech-to-text API, they're placed in the encoded_audio_landing GCS Bucket.

#### Google Cloud Storage Bucket (GCS): encoded_audio_landing

Storage location for audio files encoded so that GCP's speech-to-text API understands it. Files are deleted by subsequent processing steps to maintain state.


#### Cloud Function: encodedAudio_to_text

This function is triggered by the event of a file landing in the encoded_audio_landing bucket above. The event is received in the hello_gcs function which decodes it and passes the file name and storage bucket information to the get_transcripts function.

The get_transcripts function then uses Google's speech-to-text API to transcribe the audio recordings. It also separates the audio speaker tracks into two parts (i.e., one person on either end of the phone line).

Google's speech-to-text API is a collection of machine-learning models trained on different types of speech for specific types of transcription. We decided to use the 'medical conversation' model because we're most interested in GSK's pharmaceutical customer's medical experience. We found this model does a better job of transcribing medical terms. However, the 'phone call' model does a better job at transcribing all other words in the conversation, as the 'phone call' model is specifically trained to understand phone calls.

There's a way to use a custom dictionary of medical terms along with the phone call ML model, which would probably produce better results. However, we didn't implement that approach due to time constraints.

This function saves these transcripts to the 'transcript_landing' GCS Bucket.

#### Google Cloud Storage Bucket (GCS): transcript_landing

Storage location for unredacted transcripts stored in JSON format. Files are deleted by subsequent processing steps to maintain state.

#### Cloud Function: redaction

This function is triggered by the event of files landing on the transcript_landing GCS Bucket. The event is received in the hello_gcs function, which decodes it and passes the file name and storage bucket information to the deidentify_with_replace function.

That function then uses GCP's Data Loss Prevention API to replace certain types of specified PII, such as names, phone numbers, etc., with the string '##redacted##.'

It stores the redacted transcripts on the redacted_transcript_landing GCS storage bucket. 


#### Regex Recaction

We noticed that Google's Data Loss Prevention API failed to redact certain types of PII. So, the Data Science Team developed some rule based redaction protocols using regular expressions (regex). However, this was not included in the pipeline code. We plan to implement these rules into the pipeline if customers want to pay for this type of work in the future.

The jupyter notebook with the regex rules is included in this repo in the 'DataScience Repo ...' folder.




