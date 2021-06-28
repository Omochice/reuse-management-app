import boto3


def load_resource(name: str,
                  access_id: str,
                  access_key: str,
                  region_name: str = "ap-northeast-1"):
    resource = boto3.resource(name,
                              aws_access_key_id=access_id,
                              aws_secret_access_key=access_key,
                              region_name=region_name)
    return resource
