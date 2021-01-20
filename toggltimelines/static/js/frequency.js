var line_number = 1;

$(document).ready(function() {
	assign_default_settings()
	toggle_line_date_display()
	toggle_y_axis_type()
});

// On change of graph type...
$('body').on('change', 'input[type=radio][name=graph_type]', function() {
	toggle_y_axis_type()
	toggle_line_date_display()
	hide_show_minutes_scope()
	toggle_current_minute_checkbox()
	toggle_rolling_average_checkbox()
})

// On change of scope type...
$('body').on('change', 'input[type=radio][name=scope_type]', function() {
	toggle_y_axis_type()
	toggle_current_minute_checkbox()
	toggle_rolling_average_checkbox()
})

// On change of graph style...
$('body').on('change', 'input[type=radio][name=graph_style]', function() {
	hide_show_line_graph_checkboxes()
	toggle_current_minute_checkbox()
	toggle_trend_checkbox()
})

function toggle_trend_checkbox() {
	var graph_style = get_graph_style()
	var container = $('.trend-line-checkbox-container')

	if (graph_style == 'bar') {
		container.hide()
	} else {
		container.show()
	}
}

function assign_default_settings() {
	if (existing_lines.length == 0) {
		$('.new_frequency_line_button').click()
	}

	$("input[type='radio'][value='" + graph_type +"']").parent().click()
	$("input[type='radio'][value='" + scope_type +"']").parent().click()
	$("input[type='radio'][value='" + graph_style +"']").parent().click()

	var number_of_lines = existing_lines.length


	for (var i = existing_lines.length - 1; i >= 0; i--) {
		create_new_line_controls(existing_lines[i], i)
	}
}

function toggle_current_minute_checkbox() {
	checkbox_container = $('.day-view-live-line')
	if (is_day_view()) {
		checkbox_container.show()
	} else {
		checkbox_container.hide()
	}
}

function toggle_rolling_average_checkbox() {
	var graph_type = get_graph_type();
	var scope_type = get_scope_type();

	var element = $('.rolling-average-checkbox-container');

	if (graph_type == 'normal' && scope_type == 'days') {
		element.show();
	} else {
		element.hide();
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

	var minutes_button = $('#frequency-minutes');
	var days_button = $('#frequency-days');
	var weekday_button = $('#frequency-weekday');

	if (graph_type == 'frequency') {
		minutes_button.show()
		weekday_button.show()
		return
	}

	minutes_button.hide()
	weekday_button.hide()
	days_button.css('cssText', 'border-radius: 2px 0 0 2px !important');

	if (['minutes', 'weekday'].includes(scope_type)) {
		minutes_button.removeClass('active')
		days_button.trigger('click')
	}
}

function toggle_y_axis_type() {
	
	var graph_type = get_graph_type()
	var scope_type = get_scope_type()

	var select_element = $('#y_axis_type')

	var initially_selected = select_element.val()

	select_element.empty()

	var absolute = "<option value='absolute'>Absolute</option>"
	var average = "<option value='average'>Average Hours</option>"
	var percentage_tracked = "<option value='percentage_tracked'>Percentage of tracked time</option>"
	var percentage_occurance = "<option value='percentage_occurance'>Percentage of times project occurs</option>"

	select_element.append(absolute)
	var valid_options = ['absolute']


	if (graph_type == 'normal') return;


	if (scope_type == 'minutes') {
		select_element.append(percentage_occurance)
		valid_options.push('percentage_occurance')
	} else {
		select_element.append(average)
		valid_options.push('average')

		select_element.append(percentage_tracked)
		valid_options.push('percentage_tracked')
	}

	if (valid_options.includes(initially_selected)) {
		select_element.val(initially_selected)	
	} else {
		select_element.val('absolute')
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

$('body').on('change', '.frequency_line_label', function() {
	update_date_inputs_on_label_change(this)
})

// If the given label is a year, update the start/end inputs to fill the year. (Frequency mode only).
function update_date_inputs_on_label_change(label_input) {
	var label_value = $(label_input).val()

	if (!check_string_is_year(label_value) || get_graph_type() != 'frequency') {
		return false;
	}
	var year_start = label_value + '-01-01'

	var line_container = $(label_input).parents('form').first()
	var start_input = line_container.find('.line_start_date')
	var end_input = line_container.find('.line_end_date')

	start_input.val(year_start)

	var today = new Date();
	var current_year = today.getFullYear();
	var current_month = String(today.getMonth() + 1).padStart(2, '0');
	var current_day = String(today.getDate()).padStart(2, '0');

	if (label_value == current_year) {
		end_input.val(label_value + '-' + current_month + '-' + current_day)
	} else {
		end_input.val(label_value + '-12-31')
	}

	return true;
}

function check_string_is_year(str) {
	if (str.length != 4) {
		return false
	}

	var text = /^[0-9]+$/;

	if (!text.test(str)) {
		return false
	}

	return true


}


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

function create_new_line_controls(data={}, line_number=false) {
	$.ajax({
		"type": "POST",
		"url": "/frequency/new_frequency_line",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$('#graph_line_controllers').append(response.html)

			var project_selector = $('.frequency_project_selector').last().selectize();
			var project_selectize = project_selector[0].selectize;
			project_selectize.setValue(response.active_projects, true)

			var tag_selector = $('.frequency_tag_selector').last().selectize();
			var tag_selectize = tag_selector[0].selectize;
			tag_selectize.setValue(response.active_tags, true)

			hide_show_minutes_scope()

			if (line_number !== false && line_number >= existing_lines.length-1) {
				submit_graph_request()
			}

		}
	})
}

$('#frequency_graph_submit').on('click', function() {
	submit_graph_request()
})

function submit_graph_request() {
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
		serialized_object['rolling_average'] = $("#rolling-average-checkbox").is(':checked')
		serialized_object['cumulative'] = $("#cumulative-checkbox").is(':checked')

		graph_type = get_graph_type()
		if (graph_type == 'normal') {
			start = $('.global-start-date').val()
			serialized_object['start'] = start

			end = $('.global-end-date').val()
			serialized_object['end'] = end
		}

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
}

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

// Return true if the trend line should be displayed.
function get_display_trend_line() {
	if (!$('#trend-line-checkbox').is(":checked")) {
		return false;
	}

	if (['line', 'scatter'].includes(graph_style)) {
		return true
	}

	return false
}

function get_x_tick_values(data, width=false, x_tick_width=50, rotate_ticks=false) {
	if (graph_type == 'frequency' && scope_type == 'minutes') {
		hours = []
		for (var i = 0; i <= 24; i++) {
			hours.push(i*60)
		}

		return hours
	}
	
	var number_of_ticks = get_number_of_ticks(data)

	var tick_width = 30

	if (rotate_ticks) {
		x_tick_width = 30
	}

	var max_ticks = Math.ceil(width / x_tick_width) - 1

	ticks = []

	var step_size = Math.ceil(number_of_ticks / max_ticks)

	for (var i = 0; i <= number_of_ticks; i+=step_size) {
		ticks.push(i)
	}

	return ticks;
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
		return format_minutes(value)
	} else if (['percentage_tracked', 'percentage_occurance'].includes(y_axis_type)) {
		return value + '%'
	}

	return value
}

function format_minutes(total_minutes, clock=false) {
	var days = Math.floor(total_minutes / 1440).toString();
	var hours = Math.floor(total_minutes / 60).toString();
	var minutes = (total_minutes % 60).toString();

	if (clock) {
		if (minutes.length == 1) {
			minutes = '0' + minutes
		}

		return hours + ':' + minutes
	}

	if (total_minutes < 60*24) {
		return hours.toString() + 'h, ' + minutes.toString() + 'm';	
	}

	var hours = Math.floor( (total_minutes % 1440) / 60 )

	return days.toString() + 'd, ' + hours.toString() + 'h';

	
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
			'weekday': 'Weekday',
			'days': 'Day',
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
	var cumulative = $("#cumulative-checkbox").is(':checked')

	if (cumulative) {
		return 'Total Time'
	}

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
				'weekday': 'Total time per weekday',
				'days': 'Total time per day',
				'weeks': 'Total time per week',
				'months': 'Total time per month'
			},
			'average': {
				'weekday': 'Average time per weekday',
				'days': 'Average time per day',
				'weeks': 'Average time per week',
				'months': 'Average time per month'
			},
			'percentage_tracked': {
				'weekday': 'Percentage of total activity time',
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

function get_number_of_ticks(data) {
	var tick_counts = []

	for (var i = data.length - 1; i >= 0; i--) {
		tick_counts.push(data[i]['keys'].length)
	}

	return d3.max(tick_counts)
}

// Get the width of the text in an x-axis tick label.
function get_x_tick_width(data) {
	$('#frequency_graph_container').append("<span id='width-test'>" + data[0]['keys'][0] + "</span>")

	return $('#width-test').width() + 10; // Adding 10 to give a bit of buffer.
}

function check_need_to_rotate_x_ticks(number_of_ticks, width, x_tick_width, graph_type, scope_type) {
	if (graph_type == 'frequency' && scope_type != 'days') {
		return false;
	}

	var max_ticks = Math.ceil(width / x_tick_width) - 1

	if (number_of_ticks > max_ticks) {
		return true
	}

	return false;
}

// Calcualte an offset for the legend, based on how long the labels are.
function get_legend_x_offset(data){
	var longest_label_length = 0;
	for (var i = data.length - 1; i >= 0; i--) {
		var label = data[i]['line_data']['label'];
		var length = label.length;

		if (length > longest_label_length) {
			longest_label_length = length;
		}
	}

	var offset = 6 * longest_label_length;

	if (get_display_trend_line()) {
		offset += 100
	}

	return offset
}
	

function create_graph(data, graph_style) {
	// console.log(data)
	reset_graph_view()

	var legend_x_offset = get_legend_x_offset(data)

	var decimalFormat = d3.format("0.2f");

	var margin = {top: 10, right: 30, bottom: 100, left: 90};

	var width = $('#frequency_graph_container').width() - margin.left - margin.right;

	var number_of_ticks = get_number_of_ticks(data)

	var x_tick_width = get_x_tick_width(data)

	var need_to_rotate_x_ticks = check_need_to_rotate_x_ticks(number_of_ticks, width, x_tick_width, graph_type, scope_type)
	

	if (need_to_rotate_x_ticks) {
		margin.bottom = 140;
	};

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
			return d3.min(array['values']);
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
			.range([0, width]);
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

	var tip = d3.tip()
		.attr('class', 'd3-tip')
		.offset([-10, 0])
		.html(function(d, i) {
			line_number = d['line_number']
			label = data[line_number]['line_data']['label']
			x_value = data[line_number]['keys'][i]
			y_value = format_y_value(d['value'])

			if (graph_type == 'frequency' && scope_type == 'minutes') {
				x_value = format_minutes(x_value, true)
			}

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


		animation_durations = {
			'frequency': {
				'minutes': 500*24,
				'days': 500*12,
				'weeks': 200*53,
				'months': 500*12
			},
			'normal': {
				'days': 5000,
				'weeks': 5000,
				'months': 5000
			}
		}

		duration = animation_durations[graph_type][scope_type]
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
						.duration(duration)
						.ease(d3.easeLinear)
						.attr("stroke-dashoffset", 0)
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

	
	// Draw trend line.
	if (get_display_trend_line() /*&& ['line', 'scatter'].includes(graph_style)*/) {

		var trend_line_slopes = []

		for (var i = data.length - 1; i >= 0; i--) {
			var x_values = Object.keys(data[i]['keys']).map(function(x) {
				return parseInt(x, 10);
			});
			var y_values = data[i]['values'];

			var last_x = x_values[x_values.length-1]

			
			var least_square = LeastSquares(x_values, y_values)
			var slope = least_square['m']
			var y_intercept = least_square['b']
			var x_intercept = -y_intercept / slope

			var x1 = 0
			var x2 = x_values.length - 1

			var y1 = least_square['b']
			var y2 = y1 + x2*least_square['m']

			if (slope > 0 && x_intercept > 0) {
				x1 = x_intercept
				y1 = 0

			} else if (slope < 0 && x_intercept < x2) {
				x2 = x_intercept
				y2 = 0
			}

			var trend_data = [[x1, y1, x2, y2]]
			
			var trend_line = svg.selectAll(".trendline" + i)
				.data(trend_data);
				
			trend_line.enter()
				.append("line")
				.attr("class", "trendline")
				.attr("x1", function(d) { return x(d[0]); })
				.attr("y1", function(d) { return y(d[1]); })
				.attr("x2", function(d) { return x(d[2]); })
				.attr("y2", function(d) { return y(d[3]); })
				.attr("stroke", data[i]['line_data']['color'])
				.style("stroke-dasharray", ("3, 3"))
				.attr("stroke-width", 3);

			trend_line_slopes.unshift(least_square['m'])
		}
	}

	svg.append('g')
		.attr('class', 'x-axis')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.tickValues(get_x_tick_values(data, width, x_tick_width, need_to_rotate_x_ticks))
			.tickFormat(d => get_x_tick_format(d, data, graph_type, scope_type))
		);

	if (need_to_rotate_x_ticks) {
		svg.selectAll('.x-axis')
		.selectAll('text')
			.style('text-anchor', 'end')
			.attr('dx', '-.8em')
			.attr('dy', '.15em')
			.attr("transform", "rotate(-65)" );
	} 
	
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
			.attr('x', width - 150 - legend_x_offset)
			.attr('y', function(d, i) {
				return i * 20;
			})
			.attr('width', 12)
			.attr('height', 12)
			.style('fill', function(d) {
				return d['line_data']['color']
			});

	svg.selectAll('myLegendLabels')
		.data(data)
		.enter()
			.append('text')
			.attr('x', width - 135 - legend_x_offset)
			.attr('y', function(d, i) {
				return (i*20) + 11;
			})
			.text(function(d, i) {
				
				var label = d['line_data']['label']

				//if (!get_display_trend_line() || !['scatter', 'line'].includes(graph_style)) {
				if (!get_display_trend_line()){
					return label;
				}

				var slope = decimalFormat(trend_line_slopes[i])

				return label + ' (slope: ' + slope + ')';
			});

	if (need_to_rotate_x_ticks) {
		var x_axis_adjustment = 75
	} else {
		var x_axis_adjustment = 30
	}

	// x-axis label
	svg.append("text")             
		.attr("transform",
			"translate(" + (width/2) + " ," + 
				(height + margin.top + x_axis_adjustment) + ")")
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

function LeastSquares(values_x, values_y) {
    var sum_x = 0;
    var sum_y = 0;
    var sum_xy = 0;
    var sum_xx = 0;
    var count = 0;

    /*
     * We'll use those variables for faster read/write access.
     */
    var x = 0;
    var y = 0;
    var values_length = values_x.length;

    if (values_length != values_y.length) {
        throw new Error('The parameters values_x and values_y need to have same size!');
    }

    /*
     * Nothing to do.
     */
    if (values_length === 0) {
        return [ [], [] ];
    }

    /*
     * Calculate the sum for each of the parts necessary.
     */
    for (var v = 0; v < values_length; v++) {
        x = values_x[v];
        y = values_y[v];
        sum_x += x;
        sum_y += y;
        sum_xx += x*x;
        sum_xy += x*y;
        count++;
    }

    /*
     * Calculate m and b for the formular:
     * y = x * m + b
     */
    var m = (count*sum_xy - sum_x*sum_y) / (count*sum_xx - sum_x*sum_x);
    var b = (sum_y/count) - (m*sum_x)/count;


    return {'b': b, 'm': m};
}

function is_day_view() {
	if (get_graph_type() == 'frequency' && get_scope_type() == 'minutes') {
		return true
	}
}