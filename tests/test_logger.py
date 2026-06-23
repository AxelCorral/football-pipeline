"""Tests du logger partagé du pipeline."""

import logging

from src.utils.logger import get_logger


def test_get_logger_configures_pipeline_logger():
    logger = get_logger("tests.pipeline.logger", level=logging.DEBUG)

    assert logger.level == logging.DEBUG
    assert logger.propagate is False
    assert len(logger.handlers) == 1
    assert isinstance(logger.handlers[0], logging.StreamHandler)
    assert (
        logger.handlers[0].formatter._fmt
        == "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )


def test_get_logger_reuses_existing_handler():
    logger = get_logger("tests.pipeline.reused")
    original_handler = logger.handlers[0]

    reused_logger = get_logger("tests.pipeline.reused", level=logging.DEBUG)

    assert reused_logger is logger
    assert reused_logger.handlers == [original_handler]
    assert reused_logger.level == logging.DEBUG
