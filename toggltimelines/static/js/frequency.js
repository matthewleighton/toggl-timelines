
$(document).ready(function() {
	$('.new_frequency_line_button').click()
	toggle_line_date_display()
	toggle_y_axis_type()
})

// On change of graph type...
$('body').on('change', 'input[type=radio][name=graph_type]', function() {
	console.log('Changed graph type')
	toggle_y_axis_type()
	toggle_line_date_display()
	hide_show_minutes_scope()
	toggle_current_minute_checkbox()
})

// On change of scope type...
$('body').on('change', 'input[type=radio][name=scope_type]', function() {
	toggle_y_axis_type()
	toggle_current_minute_checkbox()
})

$('body').on('change', 'input[type=radio][name=graph_style]', function() {
	hide_show_line_graph_checkboxes()
	toggle_current_minute_checkbox()
})

function toggle_current_minute_checkbox() {
	checkbox_container = $('.day-view-live-line')
	if (is_day_view()) {
		checkbox_container.show()
	} else {
		checkbox_container.hide()
	}
}

function hide_show_line_graph_checkboxes() {
	graph_style = get_graph_style()
	checkbox_container = $('.line-graph-checkboxes')

	if (graph_style == 'line') {
		checkbox_container.show()
	} else {
		checkbox_container.hide()
	}
}

function hide_show_minutes_scope() {
	var graph_type = get_graph_type();
	var scope_type = get_scope_type();

	var minutes_button = $('#frequency-minutes')
	var days_button = $('#frequency-days')

	if (graph_type == 'frequency') {
		minutes_button.show()
		days_button.css('cssText', 'border-radius: 0 !important');
		return
	}

	minutes_button.hide()

	if (scope_type == 'minutes') {
		minutes_button.removeClass('active')
		days_button.trigger('click')
		days_button.css('cssText', 'border-radius: 2px 0 0 2px !important');
	}

}

function toggle_y_axis_type() {
	graph_type = get_graph_type()
	scope_type = get_scope_type()

	select_element = $('#y_axis_type')

	select_element.empty()

	var absolute = "<option value='absolute'>Absolute</option>"
	var average = "<option value='average'>Average Hours</option>"
	var percentage_tracked = "<option value='percentage_tracked'>Percentage of tracked time</option>"
	var percentage_occurance = "<option value='percentage_occurance'>Percentage of times project occurs</option>"

	select_element.append(absolute)

	if (graph_type == 'normal') return;

	if (scope_type == 'minutes') {
		select_element.append(percentage_occurance)
	} else {
		select_element.append(average)
		select_element.append(percentage_tracked)
	}	
}


function toggle_line_date_display() {
	graph_type = get_graph_type()
	if (graph_type == 'normal') {
		$('body').addClass('hide-line-date-controls')
		$('#global-graph-dates').removeClass('hidden')
	} else {
		$('body').removeClass('hide-line-date-controls')
		$('#global-graph-dates').addClass('hidden')
	}
}

$('#frequency_settings_button').on('click', function() {
	$('#frequency_graph_container').hide()
	$('#frequency_settings_container').show()
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

$('.new_frequency_line_button').on('click', function() {
	create_new_line_controls()
})

// Duplicate line
$('body').on('click', '.duplicate-line-button', function() {
	var $line = $(this).closest(".frequency_line_control")
	
	var description = $line.find("input[name='description']").val()
	var label = $line.find("input[name='label']").val()
	var start = $line.find("input[name='start']").val()
	var end = $line.find("input[name='end']").val()
	var color = $line.find("input[name='color']").val()
	var projects = $line.find(".frequency_project_selector")[0].selectize.getValue()

	var data = {
		'projects': projects,
		'start': start,
		'label': label,
		'description': description,
		'end': end,
		'color': color
	}
	create_new_line_controls(data)
})

function create_new_line_controls(data={}) {
	$.ajax({
		"type": "POST",
		"url": "/frequency/new_frequency_line",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$('#graph_line_controllers').append(response.html)

			var project_selector = $('.frequency_project_selector').last().selectize();
			var selectize = project_selector[0].selectize;
			selectize.setValue(response.active_projects, true)

			hide_show_minutes_scope()
		}
	})
}

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
		serialized_object['scope_type'] = $("input[type='radio'][name='scope_type']:checked").val()
		serialized_object['graph_type'] = $("input[type='radio'][name='graph_type']:checked").val()
		serialized_object['graph_style'] = $("input[type='radio'][name='graph_style']:checked").val()
		// serialized_object['scale_from_zero'] = $('#scale-from-zero').is(":checked");

		graph_type = get_graph_type()
		if (graph_type == 'normal') {
			start = $('.global-start-date').val()
			serialized_object['start'] = start

			end = $('.global-end-date').val()
			serialized_object['end'] = end
		}

		console.log(serialized_object)

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
			graph_type = get_graph_type()
			graph_style = get_graph_style()

			create_graph(response, graph_style)
		}
	})
})

function get_scope_type() {
	return $("input[name='scope_type']:checked").val()
}

function get_graph_type() {
	return $("input[name='graph_type']:checked").val()	
}

function get_graph_style() {
	return $("input[name='graph_style']:checked").val()
}

function get_animate_value() {
	return $('#animate-checkbox').is(":checked");
}

function get_show_datapoints_value() {
	return $('#show-datapoints-checkbox').is(":checked");
}

function get_show_current_time_value() {
	return $('#day-view-live-line').is(":checked");
}

function get_y_axis_type() {
	return $('#y_axis_type').val()
}

function get_scale_from_zero() {
	return $('#scale-from-zero').is(":checked")
}

function get_x_tick_values(data, width=false) {
	if (graph_type == 'frequency' && scope_type == 'minutes') {
		hours = []
		for (var i = 0; i <= 24; i++) {
			hours.push(i*60)
		}

		return hours
	} else if (graph_style == 'bar' && graph_type == 'normal') {

		last_tick = data[0]['keys'].length

		if (graph_type == 'normal' && (scope_type == 'months' || scope_type == 'weeks')) {
			width_divider = 38
		} else {
			width_divider = 60
		}

		number_of_ticks = d3.min([width/width_divider, last_tick])

		if (number_of_ticks >= last_tick) {
			return null;
		}

		step_size = Math.round(last_tick / number_of_ticks)
		ticks = []
		for (var i = 0; i <= number_of_ticks; i++) {
			ticks.push(i*step_size)
		}

		return ticks
	} else {
		return null;
	}
}

function get_x_tick_format(d, data, graph_type, scope_type) {
	if (graph_type == 'frequency' && scope_type == 'minutes') {
		return d/60
	}

	return data[0]['keys'][d]
}

function format_y_value(value) {
	var y_axis_type = get_y_axis_type()

	if (['absolute', 'average'].includes(y_axis_type)) {
		var total_minutes = value;
		var hours = Math.floor(total_minutes / 60);
		var minutes = total_minutes % 60

		return hours.toString() + 'h, ' + minutes.toString() + 'm';

	} else if (['percentage_tracked', 'percentage_occurance'].includes(y_axis_type)) {
		return value + '%'
	}

	return value
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

function get_x_axis_label() {
	var graph_type = get_graph_type()
	var scope_type = get_scope_type()

	var labels = {
		'normal': {
			'days': 'Date',
			'weeks': 'Week of Year',
			'months': 'Month'
		},
		'frequency': {
			'minutes': 'Hour of day',
			'days': 'Weekday',
			'weeks': 'Week Number',
			'months': 'Month'
		}
	}

	return labels[graph_type][scope_type]
}

function get_y_axis_label() {
	var graph_type = get_graph_type()
	var y_axis_type = get_y_axis_type()
	var scope_type = get_scope_type()

	var labels = {
		'normal': {
			'absolute': {
				'days': 'Hours per day',
				'weeks': 'Hours per week',
				'months': 'Hours per month'
			}
		},
		'frequency': {
			'absolute': {
				'minutes': 'Total time per minute',
				'days': 'Total time per weekday',
				'weeks': 'Total time per week',
				'months': 'Total time per month'
			},
			'average': {
				'days': 'Average time per weekday',
				'weeks': 'Average time per week',
				'months': 'Average time per month'
			},
			'percentage_tracked': {
				'days': 'Percentage of total activity time',
				'weeks': 'Percentage of total activity time',
				'months': 'Percentage of total activity time'
			},
			'percentage_occurance': {
				'minutes': 'Percentage of days in which activity occurs at time'
			}
		}
	}

	return labels[graph_type][y_axis_type][scope_type]
}

function create_graph(data, graph_style) {
	console.log(data)
	reset_graph_view()

	var margin = {top: 10, right: 30, bottom: 70, left: 90};

	var width = $('#frequency_graph_container').width() - margin.left - margin.right;
	var height = $(window).height() - margin.top - margin.bottom
	var min_x = 0
	var max_x = data[0]['values'].length

	var max_frequency = d3.max(data, function(array) {
		return d3.max(array['values']);
	});

	if (get_scale_from_zero()) {
		var min_frequency = 0
	} else {
		var min_frequency = d3.min(data, function(array) {
			return d3.min(array['values']) - 20;
		});

		var min_frequency = d3.max([0, min_frequency])
	}

	var y = d3.scaleLinear()
		.domain([min_frequency, max_frequency])
		.range([height, 0])
		.nice();


	if (graph_style == 'bar') {
		var element_name = 'rect';

		var x_domain = Object.keys(data[0]['keys'])

		var x = d3.scaleBand()
			.domain(x_domain)
			.range([0, width])
			.padding(0.2)

		x_range = []
		for (i = 0; i < data.length; i++){
			x_range.push(i)
		}

		var x_sub = d3.scaleBand()
			.domain(x_range)
			.range([0, x.bandwidth()])
			.padding([0.05])
		}
	else {
		var element_name = 'circle';

		var x = d3.scaleLinear()
			.domain([min_x, max_x])
			.range([0, width])
			.nice();
	}

	var svg = d3.select('#frequency_graph_container').append('svg')
				.attr('width', width)
				.attr('height', height)
			.append('g')
				.attr('transform', 'translate(' + margin.left + ',' + margin.top +')');


	var graph_elements = svg.selectAll('g')
		.data(data)
		.enter()
			.append('g')
			.selectAll(element_name)
			.data(function(d, i) {
				formatted_data = []

				for(var j = 0; j < d['values'].length; j++) {
					formatted_data.push({
						'line_number': i,
						'value': d['values'][j]
					})
				}

				return formatted_data
			})

	console.log('height')
	console.log(height)

	var tip = d3.tip()
		.attr('class', 'd3-tip')
		.offset([-10, 0])
		.html(function(d, i) {
			line_number = d['line_number']
			label = data[line_number]['line_data']['label']
			x_value = data[line_number]['keys'][i]
			y_value = format_y_value(d['value'])

			return "<div class='tooltip-title'><span>" + label + "</span></div><div>" + x_value + "</div><div>" + y_value + "</div>"
		})
		.direction(function() {
			if (graph_style == 'bar' && this.getBBox().height >= height-80) {
				return "w"
			} else if ( (graph_style == 'scatter' || graph_style == 'line') && this.getBBox().y <= 80) {
				return "w"
			} else {
				return "n"
			}
		})
		.offset(function() {
			if (graph_style == 'bar' && this.getBBox().height >= height-80) {
				return [-((this.getBBox().height / 2) - 42), 0]
			} else if ( (graph_style == 'scatter' || graph_style == 'line') && this.getBBox().y <= 80) {
				return [42, 0]
			} else {
				return [-8, 0]
			}
		})

	  svg.call(tip)

	if (graph_style == 'scatter') {
		graph_elements.enter()
				.append(element_name)
				.attr('cx', function(d, i) {
					return x(i)
				})
				.attr('cy', function(d, i) {
					return y(d['value'])
				})
				.attr('r', 4.5)
				.attr('fill', function(d, i){
					line_number = d['line_number']
					return data[line_number]['line_data']['color']
				})
				.on('mouseover', tip.show)
      			.on('mouseout', tip.hide)
	} else if (graph_style == 'line') {

		var line = d3.line()
				.x(function(d, i){
					return x(i)
				})
				.y(function(d, i) {
					return y(d)
				})
				.curve(d3.curveMonotoneX)

		var animation_duration = data[0]['keys'].length * 350
		var max_duration = 20000
		if (graph_type == 'frequency' && scope_type == 'minutes') {
			max_duration = 500*24
		} else if (graph_type == 'normal' && scope_type == 'days') {
			max_duration = (data[0]['keys']/30) * 500
		}
		animation_duration = d3.min([animation_duration, max_duration])
		animate = get_animate_value()


		// TODO: This probably isn't really how it should be done in d3, but I couldn't get the proper way to work.
		for (var i = 0; i <= data.length - 1; i++) {
			var path = svg.append('path')
				.data([data[i]['values']])
				.attr('class', 'line')
				.attr('class', 'graph_line')
				.attr('d', line)
				.attr('stroke', data[i]['line_data']['color'])

			var totalLength = path.node().getTotalLength()

			if (animate) {
				path.attr("stroke-dasharray", totalLength + " " + totalLength)
					.attr("stroke-dashoffset", totalLength)
					.transition()
						.duration(animation_duration)
						.ease(d3.easeLinear)
						.attr("stroke-dashoffset", 0);	
			}
			
		}

		show_datapoints = get_show_datapoints_value()
		if (show_datapoints) {
			graph_elements.enter()
				.append(element_name)
				.attr('cx', function(d, i) {
					return x(i)
				})
				.attr('cy', function(d, i) {
					return y(d['value'])
				})
				.attr('r', 4.5)
				.attr('fill', function(d, i){
					line_number = d['line_number']
					return data[line_number]['line_data']['color']
				})
				.on('mouseover', tip.show)
      			.on('mouseout', tip.hide)
		}

	} else if (graph_style == 'bar') {
		graph_elements.enter()
			.append('rect')
			.attr('x', function(d,i) {
				return (x(i) + x_sub(d['line_number']))
			})
			.attr('y', function(d,i) {
				return y(d['value'])
			})
			.attr('height', function(d,i) {
				return (height - y(d['value']))
			})
			.attr('width', function(d,i) {
				return x_sub.bandwidth()
			})
			.attr('fill', function(d,i) {
				line_number = d['line_number']
				return data[line_number]['line_data']['color']
			})
			.on('mouseover', tip.show)
      		.on('mouseout', tip.hide)
	}

	var number_of_ticks = d3.min([width/60, data[0]['keys'].length])

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.ticks(number_of_ticks)
			.tickValues(get_x_tick_values(data, width))
			.tickFormat(d => get_x_tick_format(d, data, graph_type, scope_type))
		);

	svg.append('g')
		.call(
			d3.axisLeft(y)
			.tickFormat(d => format_y_value(d))
		);

	// Adding current time line
	if (is_day_view() && get_show_current_time_value()) {
		var current_time_in_minutes = get_minutes_since_midnight()
		var x_position = x(Math.round(current_time_in_minutes))

		svg.append('line')
			.attr('x1', x_position)
			.attr('y1', 0)
			.attr('x2', x_position)
			.attr('y1', height)
			.style("stroke-width", 2)
			.style("stroke", "black")
			.style("fill", "none");
		}

	// Adding legend.
	svg.selectAll('myLegendDots')
		.data(data)
		.enter()
			.append('rect')
			.attr('x', width - 150)
			.attr('y', function(d, i) {
				return i * 20;
			})
			.attr('width', 12)
			.attr('height', 12)
			.style('fill', function(d) {
				console.log(d)
				return d['line_data']['color']
			});

	svg.selectAll('myLegendLabels')
		.data(data)
		.enter()
			.append('text')
			.attr('x', width - 135)
			.attr('y', function(d, i) {
				return (i*20) + 11;
			})
			.text(function(d, i) {
				return d['line_data']['label']
			});

	// x-axis label
	svg.append("text")             
		.attr("transform",
			"translate(" + (width/2) + " ," + 
				(height + margin.top + 30) + ")")
		.style("text-anchor", "middle")
		.text(get_x_axis_label());

	// y-axis label
	svg.append("text")
		.attr("transform", "rotate(-90)")
		.attr("y", 10 - margin.left)
		.attr("x",0 - (height / 2))
		.attr("dy", "1em")
		.style("text-anchor", "middle")
		.text(get_y_axis_label());


}

function is_day_view() {
	if (get_graph_type() == 'frequency' && get_scope_type() == 'minutes') {
		return true
	}
}