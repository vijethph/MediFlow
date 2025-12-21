"""
RabbitMQ Publisher for Publishing Events using aio-pika.

This module provides utilities for publishing events to RabbitMQ asynchronously.
"""

import asyncio
import json
import os
from typing import Any, Dict

import aio_pika
from aio_pika import DeliveryMode, ExchangeType
from tenacity import retry, stop_after_attempt, wait_exponential

from common.logging.logger_config import get_logger


logger = get_logger(__name__)

DEFAULT_RABBITMQ_URL = "amqp://admin:admin@localhost:5672/"
RABBITMQ_URL = os.getenv("RABBITMQ_URL", DEFAULT_RABBITMQ_URL)
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "healthcare")


class RabbitMQPublisher:
    """RabbitMQ message publisher using aio-pika."""

    def __init__(self, exchange_name: str = RABBITMQ_EXCHANGE):
        """
        Initialize RabbitMQ publisher.

        :param exchange_name: Name of the exchange
        """
        self.exchange_name = exchange_name
        self.connection = None
        self.channel = None
        self.exchange = None

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

            self.exchange = await self.channel.declare_exchange(
                name=self.exchange_name, type=ExchangeType.TOPIC, durable=True
            )

            logger.info("rabbitmq_connected", exchange=self.exchange_name)
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise

    async def publish(self, routing_key: str, message: Dict[str, Any]) -> bool:
        """
        Publish message to RabbitMQ exchange.

        :param routing_key: Routing key for the message
        :param message: Message payload as dictionary
        :return: True if published successfully
        """
        if not self.exchange:
            await self.connect()

        try:
            message_body = json.dumps(message, default=str)

            await self.exchange.publish(
                aio_pika.Message(
                    body=message_body.encode(),
                    delivery_mode=DeliveryMode.PERSISTENT,
                    content_type="application/json",
                ),
                routing_key=routing_key,
            )

            logger.info(
                "message_published",
                routing_key=routing_key,
                exchange=self.exchange_name,
            )
            return True
        except (aio_pika.exceptions.AMQPException, ValueError, TypeError) as e:
            logger.error(
                "message_publish_failed", routing_key=routing_key, error=str(e)
            )
            return False

    async def close(self) -> None:
        """Close RabbitMQ connection."""
        if self.connection and not self.connection.is_closed:
            await self.connection.close()
            logger.info("rabbitmq_connection_closed")


async def publish_event(routing_key: str, event_data: Dict[str, Any]) -> bool:
    """
    Publish event to RabbitMQ (convenience function).

    :param routing_key: Routing key for the event
    :param event_data: Event payload
    :return: True if published successfully
    """
    publisher = RabbitMQPublisher()
    try:
        await publisher.connect()
        return await publisher.publish(routing_key, event_data)
    finally:
        await publisher.close()


def publish_event_sync(routing_key: str, event_data: Dict[str, Any]) -> None:
    """
    Synchronous wrapper for publishing events (for use in sync contexts).

    :param routing_key: Routing key for the event
    :param event_data: Event payload
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = asyncio.create_task(publish_event(routing_key, event_data))
            _ = task
        else:
            loop.run_until_complete(publish_event(routing_key, event_data))
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(publish_event(routing_key, event_data))
        loop.close()
