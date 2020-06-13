$(document).ready(function() {
	$('.new_frequency_line_button').click()

})


$('#graph_line_controllers').on('click', '.frequency_control_right', function() {
	change_line_controls($(this), 1)
})

$('#graph_line_controllers').on('click', '.frequency_control_left', function() {
	change_line_controls($(this), -1)
})

$('#graph_line_controllers').on('click', '.frequency_control_remove', function() {
	var current_index = $(this).parent().index();

	var shift_value = current_index == 0 ? 1 : -1;

	change_line_controls($(this), shift_value)

	$(this).parent().remove();
})

$('#graph_line_controllers').on('change', '.frequency_project_selector', function() {
	var selected_projects = $(this).val()

	if (selected_projects.length != 1) {return}

	var label_input = $(this).parent().find('.frequency_line_label')

	projects = []

	$(this).children().each(function() {
		projects.push($(this).val())
	})

	if (label_input.val() == '' || projects.indexOf(label_input.val()) >= 0) {
		label_input.val(selected_projects[0])

		var hex_code = $(this).find(':selected').data('color')

		$(this).parent().find('.frequency_line_color').val(hex_code)

	}
})


function change_line_controls(button_element, value) {
	var current_index = button_element.parent().index();

	var max_index = $('#graph_line_controllers').children().length - 1

	if (current_index + value < 0 || current_index + value > max_index) {return}

	var line_controls = button_element.parent()

	line_controls.parent().children().eq(current_index + value).show()

	line_controls.hide()
}


$('.new_frequency_line_button').on('click', function() {
	$.ajax({
		"type": "POST",
		"url": "/new_frequency_line",
		"contentType": "application/json",
		"dataType": "json",
		success: function(response) {
			$('#graph_line_controllers').append(response)

			var new_index = $('#graph_line_controllers').children().length - 1
			$('#graph_line_controllers').children().hide()

			$('#graph_line_controllers').children().eq(new_index).show()



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

		serialized_object['y_axis_type'] = $("input[name='y_axis_type']:checked").val()
		console.log(serialized_object)


		submission_data.push(serialized_object)
	})


	$.ajax({
		"type": "POST",
		"url": "/frequency_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(submission_data),
		success: function(response) {
			create_frequency_graph(response)
		}
	})
})

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

function create_frequency_graph(data) {
    console.log('create_frequency_graph')
    //console.log(data)
    $('svg').remove()

    var y_axis_type = $("input[name='y_axis_type']:checked").val()

    var margin = {top: 10, right: 30, bottom: 50, left: 60};

	var width = $('#graph_container').width() - margin.left - margin.right;
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


	var svg = d3.select('#graph_container').append('svg')
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
		
		//console.log(data[i]['line_data'])

		console.log(data[i]['line_data']['label'])

		svg.append('path')
			.data([data[i]['minutes']])
			//.data([data[i]])
			.attr('class', 'line')
			.attr('class', 'graph_line')
			.attr('d', line)
			.attr('stroke', data[i]['line_data']['color'])		
	}

	console.log(data)

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
			return 'test'
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
	d3.select('#graph_container').on('mousemove', moved)

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