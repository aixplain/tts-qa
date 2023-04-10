import os

import boto3
import jiwer


# define a class map
def s3_link_handler(s3_link):
    # check if s3
    if s3_link.startswith("s3://"):
        # get bucket name
        bucket_name = s3_link.split("/")[2]
        # get object name
        object_path = "/".join(s3_link.split("/")[3:])
        return bucket_name, object_path


def upload_to_s3(bucket_name, object_path, file_path):
    # upload to s3
    s3 = boto3.client("s3", aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"], aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"])

    s3.upload_file(file_path, bucket_name, object_path)
    return f"s3://{bucket_name}/{object_path}"


def calculate_wer(reference, hypothesis):
    return jiwer.wer(reference, hypothesis)
