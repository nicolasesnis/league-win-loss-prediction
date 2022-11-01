import boto3
import json
import shutil
from awscli.customizations.s3.utils import split_s3_bucket_key
import streamlit as st 
import pickle
import os
import pandas as pd

s3 = boto3.client('s3', aws_access_key_id=st.secrets['aws_public_key'],
                  aws_secret_access_key=st.secrets['aws_secret_key'])


s3_resource = boto3.resource('s3', aws_access_key_id=st.secrets['aws_public_key'],
                  aws_secret_access_key=st.secrets['aws_secret_key'])


def get_all_s3_objects(s3, **base_kwargs):
    continuation_token = None
    while True:
        list_kwargs = dict(MaxKeys=1000, **base_kwargs)
        if continuation_token:
            list_kwargs['ContinuationToken'] = continuation_token
        response = s3.list_objects_v2(**list_kwargs)
        yield from response.get('Contents', [])
        if not response.get('IsTruncated'):  # At the end of the list?
            break
        continuation_token = response.get('NextContinuationToken')


def list_bucket(dir_s3_path, s3=s3, return_filenames_only=False):
    """
    Returns all the files stored in s3 bucket in a list type.
    :param dir_s3_path: the s3 path of the bucket.
    """
    bucket_name, prefix = split_s3_bucket_key(dir_s3_path)
    box = []
    for file in get_all_s3_objects(s3, Bucket=bucket_name, Prefix=prefix):
        box.append(file)
    if return_filenames_only:
        box = [b['Key'].split('/')[-1] for b in box if b['Key'].split('/')[-1] != '']
    return(box)

def create_s3_path(bucket_name, path):
    if path[-1] != '/':
        path += '/'
    s3.put_object(Bucket=bucket_name, Key=(path))



def upload_df_to_s3(df, url, s3=s3, make_public=False):
    df.to_csv('raw_data/tmp', index=None)
    bucket_name, prefix = split_s3_bucket_key(url)
    if make_public:
        s3.upload_file('tmp', bucket_name, prefix,
                       ExtraArgs={'ACL': 'public-read'})
    else:
        s3.upload_file('raw_data/tmp', bucket_name, prefix)
    os.remove('raw_data/tmp')


def upload_dict_to_s3(d, url, s3=s3, make_public=False):
    with open('raw_data/tmp.json', 'w') as f:
        json.dump(d, f)
    bucket_name, prefix = split_s3_bucket_key(url)
    if make_public:
        s3.upload_file('tmp', bucket_name, prefix,
                       ExtraArgs={'ACL': 'public-read'})
    else:
        s3.upload_file('raw_data/tmp.json', bucket_name, prefix)
    os.remove('raw_data/tmp.json')


def read_s3_df_file(url, s3=s3_resource):
    bucket_name, prefix = split_s3_bucket_key(url)
    try:
        l = s3.Object(bucket_name, prefix).get()['Body'].read().decode().split('\n')
        l = [i.split(',') for i in l]
        df = pd.DataFrame(l)
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        return df
    except Exception as e:
        return e


def read_s3_df_file(url, s3=s3_resource):
    bucket_name, prefix = split_s3_bucket_key(url)
    try:
        l = s3.Object(bucket_name, prefix).get()['Body'].read().decode().split('\n')
        l = [i.split(',') for i in l]
        df = pd.DataFrame(l)
        df.columns = df.iloc[0]
        df = df.iloc[1:]
        return df
    except Exception as e:
        return e


def read_s3_json_file(url, s3=s3_resource):
    bucket_name, prefix = split_s3_bucket_key(url)
    try:
        l = s3.Object(bucket_name, prefix).get()['Body'].read().decode()
        d = json.loads(l)
        return d
    except Exception as e:
        return 404
