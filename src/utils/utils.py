# define a class map
def s3_link_handler(s3_link):
    # check if s3
    if s3_link.startswith("s3://"):
        # get bucket name
        bucket_name = s3_link.split("/")[2]
        # get object name
        object_path = "/".join(s3_link.split("/")[3:])
        return bucket_name, object_path

