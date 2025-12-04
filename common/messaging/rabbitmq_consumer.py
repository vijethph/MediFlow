"""
RabbitMQ Consumer for Receiving Events using aio-pika.

This module provides utilities for consuming events from RabbitMQ asynchronously.
"""

import json
import os
from typing import Any, Callable, Dict

import aio_pika
from aio_pika import ExchangeType
from tenacity import retry, stop_after_attempt, wait_exponential

from common.logging.logger_config import get_logger


logger = get_logger(__name__)

DEFAULT_RABBITMQ_URL = "amqp://admin:admin@localhost:5672/"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", DEFAULT_RABBITMQ_URL)
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "healthcare")


class RabbitMQConsumer:
    """RabbitMQ message consumer using aio-pika."""

    def __init__(self, exchange_name: str = RABBITMQ_EXCHANGE, queue_name: str = ""):
        """
        Initialize RabbitMQ consumer.

        :param exchange_name: Name of the exchange
        :param queue_name: Name of the queue
        """
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        self.connection = None
        self.channel = None
        self.queue = None

    @retry(
        stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def connect(self) -> None:
        """
        Establish connection to RabbitMQ.

        :raises aio_pika.exceptions.AMQPException: If connection fails
        """
        try:
            self.connection = await aio_pika.connect_robust(RABBITMQ_URL)
            self.channel = await self.connection.channel()

            await self.channel.set_qos(prefetch_count=1)

            _ = await self.channel.declare_exchange(
                name=self.exchange_name, type=ExchangeType.TOPIC, durable=True
            )

            self.queue = await self.channel.declare_queue(
                name=self.queue_name, durable=True
            )

            logger.info(
                "rabbitmq_consumer_connected",
                exchange=self.exchange_name,
                queue=self.queue_name,
            )
        except aio_pika.exceptions.AMQPException as e:
            logger.error("rabbitmq_consumer_connection_failed", error=str(e))
            raise

    async def consume(
        self, routing_keys: list[str], callback: Callable[[Dict[str, Any]], None]
    ) -> None:
        """
        Start consuming messages from RabbitMQ.

        :param routing_keys: List of routing keys to bind
        :param callback: Callback function to process messages
        """
        if not self.queue or not self.channel:
            await self.connect()

        assert self.channel is not None
        assert self.queue is not None

        exchange = await self.channel.get_exchange(self.exchange_name)

        for routing_key in routing_keys:
            await self.queue.bind(exchange, routing_key=routing_key)
            logger.info("queue_bound", queue=self.queue_name, routing_key=routing_key)

        async def on_message(message) -> None:  # type: ignore[no-untyped-def]
            """
            Handle incoming message.

            :param message: Incoming message from RabbitMQ
            """
            async with message.process():
                try:
                    body = json.loads(message.body.decode())
                    logger.info("message_received", routing_key=message.routing_key)

                    callback(body)

                    logger.info("message_processed", routing_key=message.routing_key)
                except json.JSONDecodeError as e:
                    logger.error(
                        "message_decode_failed",
                        routing_key=message.routing_key,
                        error=str(e),
                    )
                except (ValueError, KeyError, TypeError) as e:
                    logger.error(
                        "message_processing_failed",
                        routing_key=message.routing_key,
                        error=str(e),
                    )

        await self.queue.consume(on_message)

        logger.info("consumer_started", queue=self.queue_name)

    async def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("rabbitmq_consumer_closed")
