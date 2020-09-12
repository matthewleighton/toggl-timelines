
$(document).ready(function() {
	update_y_axis_select_options()
	$('.new_frequency_line_button').click()
})

$('#frequency_settings_button').on('click', function() {
	$('#frequency_graph_container').hide()
	$('#frequency_settings_container').show()
})

$('#graph_line_controllers').on('change', '.frequency_line_color', function() {
	color = $(this).val()
	$(this).parents('form').first().find('.frequency_color_sample').css('background-color', color)
})

$('#graph_line_controllers').on('click', '.frequency_control_remove', function() {
	var current_index = $(this).parent().index();

	var shift_value = current_index == 0 ? 1 : -1;

	$(this).parents('form').first().remove();
})

$('#graph_line_controllers').on('click', '.frequency_date_reuse_icon', function() {
	var column_index = $(this).parent().index()
	var date = $(this).closest('tr').next().children().eq(column_index).find('input').val()

	$('#graph_line_controllers').children().each(function() {
		$(this).find("tr:nth-child(2)").children().eq(column_index).find('input').val(date)
	})
})


$('#graph_line_controllers').on('change', '.frequency_project_selector', function() {
	
	var selected_projects = $(this).val()

	if (selected_projects.length != 1) {return}

	var line_controls = $(this).parents('form').first()

	var label_input = line_controls.find('.frequency_line_label')
	
	if (label_input.val() == '' || label_input.val() in projects) {

		label_input.val(selected_projects[0])

		var hex_code = projects[selected_projects[0]]['color']

		line_controls.find('.frequency_line_color').val(hex_code).trigger('change')
	}
})

$('input[type=radio][name=scope_type]').change(update_y_axis_select_options)

$('.new_frequency_line_button').on('click', function() {
	$.ajax({
		"type": "POST",
		"url": "/frequency/new_frequency_line",
		"contentType": "application/json",
		"dataType": "json",
		success: function(response) {
			$('#graph_line_controllers').append(response)

			$('.frequency_project_selector').last().selectize()
		}
	})

	
})

$('#frequency_graph_submit').on('click', function() {
	
	submission_data = []

	$('.frequency_line_control').each(function() {
		serialized_data = $(this).serializeArray();

		serialized_object = {}

		for (var i = serialized_data.length - 1; i >= 0; i--) {

			name = serialized_data[i]['name']

			if (serialized_object[name]) {
				value = serialized_object[name]

				if (typeof value == 'string') {
					serialized_object[name] = [value]
				}
				
				serialized_object[name].push(serialized_data[i]['value'])

			} else {
				serialized_object[name] = serialized_data[i]['value']	
			}
						
		}

		serialized_object['y_axis_type'] = $("select[name='y_axis_type']").val()

		submission_data.push(serialized_object)
	})


	$.ajax({
		"type": "POST",
		"url": "/frequency/frequency_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(submission_data),
		success: function(response) {
			console.log(response)
			scope_type = get_scope_type()

			if (scope_type == 'minutes') {
				create_line_graph(response)
			} else {
				create_bar_graph(response, scope_type)
			}
		}
	})
})

function update_y_axis_select_options() {
	var options
	var dropdown = $("select[name='y_axis_type']")

	var selected_scope = $("input[type=radio][name=scope_type]:checked").val()

	
	var minutes_relative = $('<option></option>').attr('value', 'relative').text('Relative (Percentage of tracked project time in period)')
	var minutes_absolute = $('<option></option>').attr('value', 'absolute').text('Absolute (Total minutes tracked at time)')	

	var days_relative = $('<option></option>').attr('value', 'relative').text('Relative (Percentage of tracked project time in period)')
	var days_absolute = $('<option></option>').attr('value', 'absolute').text('Absolute (Total hours tracked on day)')
	var days_average = $('<option></option>').attr('value', 'average').text('Average hours tracked on each day')

	var months_relative = $('<option></option>').attr('value', 'relative').text('Relative (Percentage of tracked project time in period)')
	var months_absolute = $('<option></option>').attr('value', 'absolute').text('Absolute (Total hours tracked in month)')

	switch(selected_scope) {
		case 'minutes':
			options = [minutes_absolute, minutes_relative]
			break;
		case 'days':
			options = [days_average, days_absolute, days_relative]
			break;
		case 'months':
			options = [months_absolute, months_relative]
			break;
	}

	dropdown.empty()

	for (var i = options.length - 1; i >= 0; i--) {
		dropdown.append(options[i])
	}
}

function get_scope_type() {
	return $("input[name='scope_type']:checked").val()
}

function get_x_tick_values() {
	hours = []

	for (var i = 0; i <= 24; i++) {
		hours.push(i*60)
	}

	return hours
}

function get_x_tick_format(d) {
	return d/60
}

function get_y_tick_format(d, y_axis_type) {
	if (y_axis_type == 'absolute') {
		return d
	}

	return Math.round(d*1000)/10 + '%'
}

function make_y_gridlines(y) {
	return d3.axisLeft(y)
		.ticks(5)
}

function make_x_gridlines(x) {
	return d3.axisBottom(x)
		.ticks(60)
}

function get_minutes_since_midnight() {
	var now = new Date(),
    then = new Date(
        now.getFullYear(),
        now.getMonth(),
        now.getDate(),
        0,0,0),
    diff = now.getTime() - then.getTime();

    var minutes = diff / 60000

    return minutes
}


function create_bar_graph(data, user_scope) {
	reset_graph_view()

	console.log('--------------------')
	console.log(data)


	var scope_types = {
		'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
		'months': ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
	}

	var days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
	var months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
	var y_axis_type = data[0]['line_data']['y_axis_type']

	var x_domain = Object.keys(scope_types[user_scope])

    var margin = {top: 10, right: 30, bottom: 50, left: 60};

	var width = $('#frequency_graph_container').width() - margin.left - margin.right;
	var height = $(window).height() - 100 - margin.top - margin.bottom;

	var max_frequency = d3.max(data, function(array) {
		return d3.max(array[user_scope])
	})

	var yScale = d3.scaleLinear()
		.domain([0, max_frequency])
		.range([height, 0])
		.nice();

	xRange = []
	for (i = 0; i < data.length; i++){
		xRange.push(i)
	}

	var xScale = d3.scaleBand()
		.domain(x_domain)
		.range([0, width])
		.padding(0.2)

	var xSubgroup = d3.scaleBand()
		.domain(xRange)
		.range([0, xScale.bandwidth()])
		.padding([0.05])


	var svg = d3.select('#frequency_graph_container').append('svg')
				.attr('width', width)
				.attr('height', height)
			.append('g')
				.attr('transform', 'translate(' + margin.left + ',' + margin.top +')');

	var legend = svg.selectAll('g')
		.data(data)
		.enter()
		.append('g')
		.attr('class', 'legend');

	legend.append('rect')
		.attr('x', width - 150)
		.attr('y', function(d, i) {
			return i * 20;
		})
		.attr('width', 12)
		.attr('height', 12)
		.style('fill', function(d) {
			return d['line_data']['color']
		});

	legend.append('text')
		.attr('x', width - 135)
		.attr('y', function(d, i) {
			return (i*20) + 11;
		})
		.text(function(d, i) {
			return d['line_data']['label']
		});

	svg.append('g')
		.selectAll('g')
		.data(data)
		.enter()
			.append('g')
			.selectAll('rect')

			.data(function(d, i) {
				a = []
				for (var j = d[user_scope].length - 1; j >= 0; j--) {
					a.push({
						days: d[user_scope],
						months: d[user_scope],
						details: d['line_data'],
						line_number: i
					})
				}

				return a
			})
			.enter()
				.append('rect')
				.attr('x', function(d,i) {
					return (xScale(i) + xSubgroup(d['line_number']))
				})
				.attr('y', function(d,i) {
					return yScale(d[user_scope][i])
				})
				.attr('height', function(d,i) {
					return (height - yScale(d[user_scope][i]))
				})
				.attr('width', function(d,i) {
					return xSubgroup.bandwidth()
				})
				.attr('fill', function(d,i) {
					return d['details']['color']
				})

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(xScale)
			.tickValues(x_domain)
			.tickFormat(d => scope_types[user_scope][d])
		);
	
	svg.append('g')
		.call(
			d3.axisLeft(yScale)
				.tickFormat(d => bar_graph_y_tick_format(d, y_axis_type))
		);
}

function bar_graph_y_tick_format(d, y_axis_type) {
	if (y_axis_type == 'absolute' || y_axis_type == 'average') {
		return Math.round((d/60)*10) / 10
	} else {
		return Math.round(d*1000)/10 + '%'
	}
}

function reset_graph_view() {
	$('#frequency_settings_container').hide()
	$('#frequency_graph_container').show()
	$('svg').remove()
}


function create_line_graph(data) {
    reset_graph_view()

    var y_axis_type = $("select[name='y_axis_type']").val()

    var margin = {top: 10, right: 30, bottom: 50, left: 60};

	var width = $('#frequency_graph_container').width() - margin.left - margin.right;
	var height = $(window).height() - 100 - margin.top - margin.bottom;

	var max_time = 1439
	var min_time = 0

	var max_frequency = d3.max(data, function(array) {
		return d3.max(array['minutes']);
	});

	var min_frequency = 0;
	
	var y = d3.scaleLinear()
		.domain([0, max_frequency])
		.range([height, 0])
		.nice();

	var x = d3.scaleLinear()
		.domain([min_time, max_time])
		.range([0, width])
		.nice();


	var svg = d3.select('#frequency_graph_container').append('svg')
				.attr('width', width)
				.attr('height', height)
			.append('g')
				.attr('transform', 'translate(' + margin.left + ',' + margin.top +')');

	var line = d3.line()
					.x(function(d, i){
						return x(i)
					})
					.y(function(d){
						return y(d)
					});

	for (var i = 0; i <= data.length - 1; i++) {
		svg.append('path')
			.data([data[i]['minutes']])
			//.data([data[i]])
			.attr('class', 'line')
			.attr('class', 'graph_line')
			.attr('d', line)
			.attr('stroke', data[i]['line_data']['color'])		
	}

	var legend = svg.selectAll('g')
		.data(data)
		.enter()
		.append('g')
		.attr('class', 'legend');

	legend.append('rect')
		.attr('x', width - 150)
		.attr('y', function(d, i) {
			return i * 20;
		})
		.attr('width', 12)
		.attr('height', 12)
		.style('fill', function(d) {
			return d['line_data']['color']
		});

	legend.append('text')
		.attr('x', width - 135)
		.attr('y', function(d, i) {
			return (i*20) + 11;
		})
		.text(function(d, i) {
			return d['line_data']['label']
		});

	var current_time_in_minutes = get_minutes_since_midnight()

	svg.append('line')
		.attr('x1', x(current_time_in_minutes))
		.attr('y1', 0)
		.attr('x2', x(current_time_in_minutes))
		.attr('y1', height)
		.style("stroke-width", 2)
		.style("stroke", "black")
		.style("fill", "none");

	



	// TODO: Currently this only takes into account y distance. It needs to also consider x axis distance to lines.
	function moved() {
		const mouse = d3.mouse(this)
		const xm = Math.floor(x.invert(mouse[0])) - 52
		const ym = y.invert(mouse[1])

		//console.log('X: ' + xm)
		//console.log('Y: ' + ym)

		// Mouse must be within 10% of the graph to trigger.
		lowest_difference = y.domain()[1] / 10

		lowest_difference_index = false

		for (var i = data.length - 1; i >= 0; i--) {

			y_value = data[i]['minutes'][xm]


			diff = Math.abs(ym - y_value)

			if (diff < lowest_difference) {
				lowest_difference = diff
				lowest_difference_index = i
			}

		}

		svg.selectAll('.graph_line')
			.attr('stroke', function(d, i) {
				if (lowest_difference_index === false || i == lowest_difference_index) {
					return data[i]['line_data']['color']
				} else {
					return '#ddd'
				}
			})
	}

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.tickValues(get_x_tick_values())
			.tickFormat(d => get_x_tick_format(d))
		);
	
	svg.append('g')
		.call(
			d3.axisLeft(y)
			.tickFormat(d => get_y_tick_format(d, y_axis_type))
		);

	//svg.on('mousemove', moved)
	d3.select('#frequency_graph_container').on('mousemove', moved)

	/* GRID LINES-------
	svg.append('g')
		.attr('class', 'grid')
		.call(make_y_gridlines(y)
			.tickSize(-width)
			.tickFormat('')
		);

	svg.append('g')
		.attr('class', 'grid')
		.attr("transform", "translate(0," + height + ")")
		.call(make_x_gridlines(x)
			.tickSize(-height)
			.tickFormat('')
		);
	*/

}