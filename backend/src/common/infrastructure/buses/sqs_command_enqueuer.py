from dataclasses import dataclass

# import boto3
from src.common.domain.buses.async_commands import CommandEnqueuer
from src.common.domain.buses.commands import Command


@dataclass
class SQSCommandEnqueuer(CommandEnqueuer):
    queue_url: str

    def enqueue(self, command: Command):
        pass
        # client = boto3.client("sqs")
        # command_name = command.__class__.__name__
        # return client.send_message(
        #     QueueUrl=self.queue_url,
        #     MessageBody=json.dumps(
        #         {
        #             "command": command_name,
        #             "payload": command.to_dict,
        #         }
        #     ),
        #     MessageAttributes={
        #         "command": {
        #             "StringValue": command_name,
        #             "DataType": "String",
        #         },
        #     },
        # )
