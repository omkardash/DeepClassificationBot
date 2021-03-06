# -*- coding: utf-8 -*-
import os
import time
from multiprocessing import TimeoutError
import json

import h5py
import cv2
import pytest
import requests
import six

import deploy
import data
from deepanimebot import classifiers
from deepanimebot import exceptions as exc
import mocks


TEST_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', '1920x1080.png')


def test_fetch_cvimage_from_url(monkeypatch):
    with open(TEST_IMAGE_PATH, 'rb') as f:
        image = f.read()
    monkeypatch.setattr(requests, 'get', mocks.mock_get(image))
    image = classifiers.fetch_cvimage_from_url('this url is ignored')
    assert image is not None


def test_fetch_cvimage_from_url_non_image(monkeypatch):
    monkeypatch.setattr(requests, 'get', mocks.mock_get('non-image string'))
    image = classifiers.fetch_cvimage_from_url('this url is ignored')
    assert image is None


def test_fetch_cvimage_from_url_timeout(monkeypatch):
    def long_func(*args, **kwargs):
        time.sleep(3)
    monkeypatch.setattr(requests, 'get', long_func)
    with pytest.raises(TimeoutError):
        classifiers.fetch_cvimage_from_url('this url is ignored', timeout_max_timeout=1)


def test_fetch_cvimage_from_url_too_large(monkeypatch):
    monkeypatch.setattr(requests, 'get', mocks.mock_get('12'))
    with pytest.raises(ValueError):
        classifiers.fetch_cvimage_from_url('this url is ignored', maxsize=1)


def test_mock_classifier_classify():
    classifier = classifiers.MockClassifier()
    y = classifier.classify()
    assert isinstance(y, list)
    assert isinstance(y[0], deploy.Prediction)


def test_image_classifier_classify(monkeypatch):
    # TODO: add fixture for categories and mean. (95 is a magic number corresponding to the deployed model)
    monkeypatch.setattr(data, 'get_categories', lambda: dict((str(n), n) for n in range(95)))
    monkeypatch.setattr(data, 'get_mean', lambda path: None)
    cvimage = cv2.imread(TEST_IMAGE_PATH)
    # TODO: add fixture for weights and refactor so that model is loaded from a workspace directory
    classifier = classifiers.ImageClassifier('ignored path', 128, 'deep_anime_model')
    y = classifier.classify(cvimage)
    assert isinstance(y, list)
    assert isinstance(y[0], deploy.Prediction)


def create_url_classifier(monkeypatch):
    # TODO: add fixture for categories and mean. (95 is a magic number corresponding to the deployed model)
    monkeypatch.setattr(data, 'get_categories', lambda: dict((str(n), n) for n in range(95)))
    monkeypatch.setattr(data, 'get_mean', lambda path: None)
    # TODO: add fixture for weights and refactor so that model is loaded from a workspace directory
    image_classifier = classifiers.ImageClassifier('ignored path', 128, 'deep_anime_model')
    return classifiers.URLClassifier(image_classifier)


def test_url_classifier_classify(monkeypatch):
    with open(TEST_IMAGE_PATH, 'rb') as f:
        image = f.read()
    monkeypatch.setattr(requests, 'get', mocks.mock_get(image))
    url_classifier = create_url_classifier(monkeypatch)
    y = url_classifier.classify(TEST_IMAGE_PATH)
    assert isinstance(y, list)
    assert isinstance(y[0], deploy.Prediction)


def test_url_classifier_classify_none(monkeypatch):
    monkeypatch.setattr(classifiers, 'fetch_cvimage_from_url', lambda url: None)
    url_classifier = create_url_classifier(monkeypatch)
    with pytest.raises(exc.NotImage):
        url_classifier.classify(TEST_IMAGE_PATH)


def test_remote_classifier_classify(monkeypatch):
    response = json.dumps(dict(y=[dict(rank=1, category='noein', probability=1.0)]))
    monkeypatch.setattr(requests, 'get', mocks.mock_get(response))
    classifier = classifiers.RemoteClassifier('base url')
    y = classifier.classify(url='param')
    assert isinstance(y, list)
    assert isinstance(y[0], deploy.Prediction)


def test_remote_classifier_classify(monkeypatch):
    response = json.dumps(dict(error='something went wrong expectedly'))
    monkeypatch.setattr(requests, 'get', mocks.mock_get(response))
    classifier = classifiers.RemoteClassifier('base url')
    with pytest.raises(exc.RemoteError):
        classifier.classify(url='param')
