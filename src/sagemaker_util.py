import streamlit as st 
from src.s3 import list_bucket
import time
from botocore.client import Config
import boto3
from awscli.customizations.s3.utils import split_s3_bucket_key
import sagemaker

sm = boto3.Session().client('sagemaker',
                        aws_access_key_id=st.secrets['aws_public_key'],
                  aws_secret_access_key=st.secrets['aws_secret_key'],
                  region_name='us-west-1'
                  )
sm_runtime = sm = boto3.Session().client('sagemaker-runtime',
                        aws_access_key_id=st.secrets['aws_public_key'],
                  aws_secret_access_key=st.secrets['aws_secret_key'],
                  region_name='us-west-1'
                  )

s3_resource = boto3.resource('s3', 
                    aws_access_key_id=st.secrets['aws_public_key'],
                  aws_secret_access_key=st.secrets['aws_secret_key'])


def cleanup_boto3(experiment_name):
    trials = sm.list_trials(ExperimentName=experiment_name)['TrialSummaries']
    print('TrialNames:')
    for trial in trials:
        trial_name = trial['TrialName']
        print(f"\n{trial_name}")

        components_in_trial = sm.list_trial_components(TrialName=trial_name)
        print('\tTrialComponentNames:')
        for component in components_in_trial['TrialComponentSummaries']:
            component_name = component['TrialComponentName']
            print(f"\t{component_name}")
            sm.disassociate_trial_component(TrialComponentName=component_name, TrialName=trial_name)
            try:
                # comment out to keep trial components
                sm.delete_trial_component(TrialComponentName=component_name)
            except:
                # component is associated with another trial
                continue
            # to prevent throttling
            time.sleep(.5)
        sm.delete_trial(TrialName=trial_name)
    sm.delete_experiment(ExperimentName=experiment_name)
    print(f"\nExperiment {experiment_name} deleted")


def predict(endpoint_name, input):
    response = sm_runtime.invoke_endpoint(EndpointName=endpoint_name, ContentType='text/csv', Body=input)
    return response['Body'].read().decode()

# input = "4519157822,28,2,1,9,6,11,0,0,0,0,17210,6.6,17039,195,36,643,-8,19.5,1721,15,6,0,6,9,8,0,0,0,0,16567,6.8,17047,197,55,-643,8,19.7,1656.7"
# predict('test-endpoint-5',input)
