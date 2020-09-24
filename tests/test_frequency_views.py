import pytest
from flask import g, session
from datetime import datetime

from toggltimelines.frequency import views

def test_get_line_data_container_frequency_minutes():
	graph_type = 'frequency'
	scope_type = 'minutes'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 1, 5)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	assert list(line_data_container.keys()) == list(range(1440))

def test_get_line_data_container_frequency_weekdays():
	graph_type = 'frequency'
	scope_type = 'days'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 1, 5)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	expected = {
		'Monday': 0,
		'Tuesday': 0,
		'Wednesday': 0,
		'Thursday': 0,
		'Friday': 0,
		'Saturday': 0,
		'Sunday': 0
	}

	assert line_data_container == expected

def test_get_line_data_container_frequency_months():
	graph_type = 'frequency'
	scope_type = 'months'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 1, 5)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	expected = {
		'January': 0,
		'February': 0,
		'March': 0,
		'April': 0,
		'May': 0,
		'June': 0,
		'July': 0,
		'August': 0,
		'September': 0,
		'October': 0,
		'November': 0,
		'December': 0
	}

	assert line_data_container == expected

def test_get_line_data_container_normal_minutes():
	graph_type = 'normal'
	scope_type = 'minutes'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 1, 5, 23, 59)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	assert len(line_data_container) == 24*60*5
	assert line_data_container['2020-01-01 00:00'] == 0
	assert line_data_container['2020-01-05 23:59'] == 0

def test_get_line_data_container_normal_days():
	graph_type = 'normal'
	scope_type = 'days'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 1, 5, 23, 59)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	assert len(line_data_container) == 5
	assert line_data_container['2020-01-01'] == 0
	assert line_data_container['2020-01-05'] == 0

def test_get_line_data_container_normal_days():
	graph_type = 'normal'
	scope_type = 'months'
	start = datetime(2020, 1, 1)
	end = datetime(2020, 3, 5, 23, 59)

	line_data_container = views.get_line_data_container(graph_type, scope_type, start, end)

	assert len(line_data_container) == 3
	assert line_data_container['2020-01'] == 0
	assert line_data_container['2020-03'] == 0