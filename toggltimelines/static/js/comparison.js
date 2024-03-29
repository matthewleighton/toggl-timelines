const monthNames = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"
];

$(document).ready(function() {
	
	// Update text for "This month vs. same month last year"
	current_month_name = monthNames[new Date().getMonth()]
	$('#calendar_period option[value="month-of-year').text('This month vs. ' + current_month_name + ' last year')

	set_defaults()


	$( "#comparison_form" ).on( "submit", function( event ) {
		event.preventDefault();
		submit_comparison_form()
	});

	$('#comparison_form').change(function(e) {
		if (e.target.name == 'weekdays') {
			clearTimeout(window.weekday_timeout);

			window.weekday_timeout = setTimeout(function() {
				$('#comparison_form').submit()				
			}, 800)
		} else {
			$('#comparison_form').submit()

		}
	});





	$('#comparison_form').submit()





	$('.comparison_reload').click(function() {
		submit_comparison_form(true)
	})

	$('#comparison_weekday_selection input:checkbox').change(function() {
		var id = $(this).attr('id');
		var checked = $(this).attr('checked');
		
		if (id == 'all_weekdays' && this.checked) {

			$('input[name=weekdays]').each(function() {
				if (!this.checked) {
					$(this).click();
				}
			})

		} else if (id == 'all_weekdays') {
			$('input[name=weekdays]').each(function() {
				if (this.checked) {
					$(this).click();
				}
			})
		}
	});

	$('input[type=radio][name=period_type]').change(function() {
		change_displayed_settings(this.value)
	});

	$('#set_detault_comparison').click(function() {
		
		serialized_data = get_serialized_data()

		$.ajax({
			"type": "POST",
			"url": "/comparison/set_default",
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify(serialized_data),
			success: function(response) {
								
			}
		})
	})

	
});

function change_displayed_settings(period_type) {
	if (period_type == 'calendar') {
        $('.custom_comparison_settings').hide()
        $('.goals_comparison_settings').hide()
        $('.calendar_comparison_settings').css('display', 'flex')
    }
    else if (period_type == 'custom') {
        $('.calendar_comparison_settings').hide()
        $('.goals_comparison_settings').hide()
        $('.custom_comparison_settings').css('display', 'flex')
    }
    else if (period_type == 'goals') {
        $('.calendar_comparison_settings').hide()
        $('.custom_comparison_settings').hide()
        $('.goals_comparison_settings').css('display', 'flex')
    }
}

// Set the default configuration values, depending out the values saved in our session.
function set_defaults() {
	// console.log(comparison_defaults)

	// Radio Buttons
	period_type = comparison_defaults['period_type'] ? comparison_defaults['period_type'] : 'calendar'
	sort_type = comparison_defaults['sort_type'] ? comparison_defaults['sort_type'] : 'ratio'
	calendar_period = comparison_defaults['calendar_period'] ? comparison_defaults['calendar_period'] : 'week'

	$('input:radio[name=period_type][value=' + period_type + ']').prop('checked', true)
	$('input:radio[name=sort_type][value=' + sort_type + ']').prop('checked', true)
	$('#calendar_period option[value=' + calendar_period + ']').prop('selected', true)

	// Dropdowns
	timeframe = comparison_defaults['timeframe'] ? comparison_defaults['timeframe'] : 7
	datarange = comparison_defaults['datarange'] ? comparison_defaults['datarange'] : 7
	goals_period = comparison_defaults['goals_period'] ? comparison_defaults['goals_period'] : 'month'	

	$('#timeframe').val(timeframe)
	$('#datarange').val(datarange)
	$('#goals_period').val(goals_period)

	// Check Boxes
	live_mode_calendar = comparison_defaults['live_mode_calendar'] ? true : false
	live_mode_goals = comparison_defaults['live_mode_goals'] ? true : false
	hide_completed = comparison_defaults['hide_completed'] ? true : false
	include_empty_projects = comparison_defaults['include_empty_projects'] ? true : false
	all_weekdays = comparison_defaults['all_weekdays'] ? true : false
	show_projects = comparison_defaults['show_projects'] ? true : false
	show_clients = comparison_defaults['show_clients'] ? true : false


	$('#live_mode_calendar').prop('checked', live_mode_calendar)
	$('#live_mode_goals').prop('checked', live_mode_goals)
	$('#hide_completed').prop('checked', hide_completed)
	$('#include_empty_projects').prop('checked', include_empty_projects)
	$('#all_weekdays').prop('checked', all_weekdays)
	$('#show_projects').prop('checked', show_projects)
	$('#show_clients').prop('checked', show_clients)



	// Weekdays
	weekdays = comparison_defaults['weekdays'] ? comparison_defaults['weekdays'] : [0, 1, 2, 3, 4, 5, 6]

	for (var i = weekdays.length - 1; i >= 0; i--) {
		$('input:checkbox[name=weekdays][value=' + weekdays[i] + ']').prop('checked', true)		
	}

	change_displayed_settings(period_type)
}

function get_period_type() {
	return $('input[type=radio][name=period_type]:checked').val();
}

function get_goals_time_window() {
	return $("#goals_period option:selected").val();
}

function get_goals_live_mode() {
	return $("#live_mode_goals").is(":checked");
}

function get_serialized_data(reload=false) {
	serialized_data = $("#comparison_form").serializeArray();

	if (reload) {
		serialized_data.push({name: 'reload', value: true})
	}

	serialized_data = format_serialized_data(serialized_data);

	return serialized_data
}

function submit_comparison_form(reload=false) {
	serialized_data = get_serialized_data(reload)

	sort_type = $('input[type=radio][name=sort_type]:checked').val()

	$.ajax({
		"type": "POST",
		"url": "/comparison/data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(serialized_data),
		success: function(response) {

			if (serialized_data['period_type'] == 'calendar' && !serialized_data['include_empty_projects']) {
				response = remove_projects_with_no_current_time(response)
			}

			if (serialized_data['period_type'] == 'goals' && !response.length ) {
				toggle_goals_completed_message(true)
			} else {
				toggle_goals_completed_message(false)
				create_graph(response, sort_type)				
			}

		}
	})
}

function remove_projects_with_no_current_time(data) {
	data = $.grep(data, function(project, i) {
		if (project['current_tracked'] > 0) {
			return true;
		}

		return false;
	})

	return data
}

function format_serialized_data(data) {
	array = {}

	$.each(data, function() {
		if (array[this.name]) {
			if (!array[this.name].push) {
				array[this.name] = [array[this.name]];
			}
			array[this.name].push(this.value || '');
		} else {
			array[this.name] = this.value || '';
		}
	})

	return array
}


function get_bar_value_label(value, sort_type) {
	if (sort_type == 'ratio') {
		
		if (value == 100) {
			return "∞"
		}
		
		value = Math.round(value*100) - 100

		sign = Math.sign(value) > 0 ? '+' : ''

		return sign + value + '%'
	} else if (sort_type == 'difference') {
		sign = value < 0 ? '-' : ''

		return sign + format_seconds(Math.abs(value), true)
	}
}

function format_seconds(seconds, short=false) {
	if (short) {
		day_singular = day_plural = 'd '
		hour_singular = hour_plural = 'h '
		minute_singular = minute_plural = 'm '
		second_singular = second_plural = 's '
	} else {
		day_singular = ' day, '
		day_plural = ' days, '

		hour_singular = ' hour, '
		hour_plural = ' hours, '

		minute_singular = ' minute, '
		minute_plural = ' minutes, '

		second_singular = ' second '
		second_plural = ' seconds '
	}

	var timestamp = 9462;

	var days = Math.floor(seconds / (3600 * 24));
	seconds = seconds - days * 3600*24

	var hours = Math.floor(seconds / 60 / 60);
	var minutes = Math.floor(seconds / 60) - (hours * 60);
	var seconds = Math.floor(seconds % 60);

	var days_label = (days == 1) ? day_singular : day_plural
	var hours_label = (hours == 1) ? hour_singular : hour_plural
	var minutes_label = (minutes == 1) ? minute_singular : minute_plural
	var seconds_label = (minutes == 1) ? second_singular : second_plural

	return_string = ""

	if (days > 0) {
		return_string += days + days_label
	}	

	if (hours > 0) {
		return_string += hours + hours_label
	}

	if (minutes > 0) {
		return_string += minutes + minutes_label
	}

	if (seconds > 0) {
		return_string += seconds + seconds_label
	}

	if (return_string == "") {
		return_string = "0 " + second_plural
	}

	return return_string

	return hours + hours_label + minutes + minutes_label + seconds + seconds_label
}

function get_current_period_string() {
	var period_type = $('input[name="period_type"]:checked').val();

	if (period_type == 'custom') {

		var current_period_number = $('#timeframe').val();
		switch (current_period_number) {
			case '1':
				return 'Today: '
			case '7':
				return 'Past 7 days: '
			case '30':
				return 'Past 30 days: '
			case '365':
				return 'Past 365 days: '
		}

		return 'This period: '

	} else {
		var period = (period_type == 'calendar') ? $("#calendar_period").val() : $("#goals_period").val()

		switch (period) {
			case 'day':
				return 'Today: '
			case 'week':
				return 'This week: '
			case 'month':
				return 'This month: '
			case 'quarter':
				return 'This quarter: '
			case 'half-year':
				return 'This year half: '
			case 'year':
			case 'month-of-year':
				return 'This year: '
		}
	}
}

function get_average_label() {
	var period_type = $('input[name="period_type"]:checked').val();

	if (period_type == 'custom') {
		
		var current_period_number = $('#timeframe').val();
		var comparison_period_number = $('#datarange').val();

		if (current_period_number !== comparison_period_number) {
			if (current_period_number == 1) {
				return 'Daily average: '
			} else {
				return current_period_number + ' day average: '
			}

			return "Average: ";
		}

		if (current_period_number == 1) {
			return 'Yesterday: '
		} else {
			return 'Previous ' + current_period_number + ' days: '
		}

		return 'Average: '

	} else if (period_type == 'calendar') {

		var calendar_period = $("#calendar_period").val()

		switch (calendar_period) {
			case 'day':
				return 'Yesterday: '
			case 'week':
				return 'Last week: '
			case 'month':
				return 'Last month: '
			case 'quarter':
				return 'Last quarter: '
			case 'half-year':
				return 'Last year half: '
			case 'year':
			case 'month-of-year':
				return 'Last year: '
		}
	} else if (period_type == 'goals') {
		return 'Goal: '
	}
}

// Get the formatting of the x axis ticks.
function get_x_axis_tick(value, sort_type) {
	if (sort_type == 'ratio') {
		percentage =  ((value - 1) * 100).toFixed(0)
		if (percentage > 0) {
			percentage = "+" + percentage
		}

		return percentage + "%"
	} else if (sort_type == 'difference') {
		return format_seconds(Math.abs(value), true)
	}
}

// Get the values at which we display ticks on the x axis.
function get_x_axis_tick_values(data, sort_type, width) {
	if (sort_type == 'ratio') {
		return null // Use default value calculated by d3.
	} else if (sort_type == 'difference') {
		lowest = 0
		highest = 0

		for (var i = data.length - 1; i >= 0; i--) {
			value = data[i].difference

			if (value < lowest) {
				lowest = value
			} else if (value > highest) {
				highest = value
			}

		}

		max_allowed_ticks = Math.floor(width / 80)

		negative_hours = Math.floor(lowest / 3600)
		positive_hours = Math.ceil(highest / 3600)

		total_ticks = positive_hours + Math.abs(negative_hours)

		step = Math.ceil(total_ticks / max_allowed_ticks)

		if (total_ticks < max_allowed_ticks) {
			step = total_ticks / max_allowed_ticks
			step = Math.round(step / 0.25) * 0.25
		}

		step = (step != 0) ? step : 0.25

		ticks = [0]

		for (var i = -step; i >= negative_hours; i -= step) {
			tick_value = i * 3600

			if (tick_value > lowest - 3600/4) {
				ticks.push(tick_value)
			}
		}

		for (var i = step; i <= positive_hours; i += step) {
			tick_value = i * 3600
			
			if (tick_value < highest + 3600/4) {
				ticks.push(tick_value)
			}
		}

		return ticks
	}
}

function get_upper_x_domain_bound(data, sort_type) {
	var max_allowed
	switch (sort_type) {
		case 'ratio':
			max_allowed = 4
			break
		case 'difference':
			max_allowed = 60*60*1000 //1000 hours
	}

	max_value = 0

	for (var i = data.length - 1; i >= 0; i--) {
		value = data[i][sort_type]

		if (value > max_value && value < max_allowed) {
			max_value = value
		}
	}

	if (sort_type == 'ratio') {
		return (max_value < 2) ? 2 : max_value + 0.1	
	} else if (sort_type == 'difference') {
		return max_value + 3600/4
	}
	
}

function get_lower_x_domain_bound(data, sort_type) {
	if (sort_type == 'ratio') {
		return 0
	}

	min_ratio = 0

	for (var i = data.length - 1; i >= 0; i--) {
		ratio = data[i][sort_type]

		if (ratio < min_ratio) {
			min_ratio = ratio
		}
	}

	return min_ratio - 3600
}

function create_graph(data, sort_type) {	
	$('svg').remove()
	$('.d3-tip').remove()

	var lower_x_domain_bound = get_lower_x_domain_bound(data, sort_type)
	var upper_x_domain_bound = get_upper_x_domain_bound(data, sort_type)

	var width = $('#graph_container').width()
	var half_width = width/2
	var margin = ({top: 30, right: 60, bottom: 10, left: 60})
	var bar_height = 35
	var height = Math.ceil((data.length + 0.1) * bar_height) + margin.top + margin.bottom
	//var tooltip = d3.select("body").append("div").attr("class", "toolTip");

	var current_period_string = get_current_period_string()
	
	var x_position = d3.scaleLinear()
					.domain([lower_x_domain_bound, upper_x_domain_bound])
					.rangeRound([margin.left, width - margin.right])
					.clamp(true);
	
	var y_position = d3.scaleBand()
    	.domain(d3.range(data.length))
    	.rangeRound([margin.top, height - margin.bottom])
    	.padding(0.1)
	  
	var canvas = d3.select("#graph_container")
				.append("svg")
				.attr("width", width)
				.attr("height", height);

	x_axis_tick_values = get_x_axis_tick_values(data, sort_type, width)

	yAxis = g => g
    .attr("transform", `translate(${x_position(1)},0)`)
    .call(d3.axisLeft(y_position).tickFormat(i => data[i].name).tickSize(0).tickPadding(6))
    .call(g => g.selectAll(".tick text").filter(i => data[i][sort_type] < 1)
        .attr("text-anchor", "start")
        .attr("x", 6))
   	//.call(g => g.select(".domain").remove())

    xAxis = g => g
    	.attr("transform", `translate(0,${margin.top})`)
    	.call(d3
    		.axisTop(x_position)
    		.ticks(width / 80)
    		.tickFormat(d => get_x_axis_tick(d, sort_type))
    		.tickValues(x_axis_tick_values)
    	)
    	.call(g => g.select(".domain").remove())

    canvas.append("g")
    	.call(yAxis);

    canvas.append("g")
    	.call(xAxis);

    var tip = d3.tip()
	  .attr('class', 'd3-tip')
	  .offset([-10, 0])
	  .html(function(d) {
	    current_tracked = format_seconds(d.current_tracked)
	    average = format_seconds(d.average)

	    average_label = get_average_label()

	    difference_seconds = Math.abs(d.difference)
	    difference_string = format_seconds(difference_seconds)

	    tooltip = "<strong>" + d.name + "</strong><div><span>" + current_period_string + "</span>" + current_tracked + "</div><div><span>" + average_label + "</span>" + average + "</div><div><span>Difference: </span>" + difference_string + "</div>";

	    period_type = get_period_type()
	    goals_time_window = get_goals_time_window()
	    goals_live_mode = get_goals_live_mode()

	    // If we're in goals mode, and the remaining time is less than a day,
	    // display the earliest possible completion time in the tooltip.
	    if (period_type == 'goals' && -86400 < d.difference && d.difference < 0 
	    	/*&& goals_time_window == 'day' && !goals_live_mode*/) {
			possible_completion = get_goal_possible_completion_time(difference_seconds)
			tooltip += "<div><span>Possible Completion:</span> " + possible_completion + "</div>";	
	    }

	    return tooltip
	  })

	canvas.call(tip)

	canvas.append("g")
		.selectAll("rect")
		.data(data)
		.join("rect")
			.attr("fill", d => d.color)
			.attr("x", d => x_position(Math.min(d[sort_type], 1)))
			.attr("y", (d, i) => y_position(i))
			.attr("width", d => Math.abs(x_position(d[sort_type]) - x_position(1)))
			.attr("height", y_position.bandwidth())
			.on('mouseover', tip.show)
      		.on('mouseout', tip.hide)
			
	
	canvas.append("g")
		.attr("font-family", "sans-serif")
		.attr("font-size", 10)
		.selectAll("text")
		.data(data)
		.join("text")
			.attr("text-anchor", d => d[sort_type] < 1 ? "end" : "start")
			.attr("x", d => x_position(d[sort_type]) + Math.sign(d[sort_type] - 1) * 4)
			.attr("y", (d, i) => y_position(i) + y_position.bandwidth() / 2)
			.attr("dy", "0.35em")
			.text(d => get_bar_value_label(d[sort_type], sort_type));
}

function get_goal_possible_completion_time(remainging_seconds) {
	completion_time = new Date();
    completion_time.setSeconds(completion_time.getSeconds() + remainging_seconds)

    hour = completion_time.getHours();
    minute = (completion_time.getMinutes() < 10 ? '0' : '') + completion_time.getMinutes();

    return hour + ":" + minute
}

function toggle_goals_completed_message(goals_completed) {
	if (!goals_completed) {
		$('#goals_completed_message').hide()
		return true
	}

	$('svg').remove()
	$('.d3-tip').remove()

	all_emojis = ['🐢', '🦙', '🎉', '✨', '🌈', '🔥', '🎆', '🍕', '🍨', '🍩', '🏆', '🏅', ]
	emoji_1 = all_emojis[Math.floor(Math.random() * all_emojis.length)];
	emoji_2 = all_emojis[Math.floor(Math.random() * all_emojis.length)];

	message = emoji_1 + ' All goals completed! ' + emoji_2

	$('#goals_completed_message').html(message)	

	$('#goals_completed_message').show()
}