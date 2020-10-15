var current_node = false
var max_node_number = 1

$(document).ready(function() {
	$('tr').last().addClass('history-table-averages')
	$('tr').last().prev().addClass('history-table-final-year')

	update_details_div();

	$('body').keydown(function(e) {
		var keyCode = e.originalEvent.keyCode

		if (current_node && (keyCode == 37 || keyCode == 39)) {

			var load_new = false;

			if (keyCode == 37 && current_node > 1) { // Left
				current_node--;
				load_new = true;
			} else if (keyCode == 39 && current_node < max_node_number) { // Right
				current_node++;
				load_new = true;
			}

			if (load_new) {
				document.getElementById('node-' + current_node).dispatchEvent(new Event('click'));
			}
		} else if (keyCode == 27) {
			document.getElementsByClassName('graph-readthrough-close')[0].dispatchEvent(new Event('click'));
		}

	})
})



$('#reading-year').change(function() {
	update_details_div()
});

$('input[type=radio][name=history_type]').change(function() {
	var value = $(this).val();

	if (value == 'details') {
		$('#reading-history-details').show();
		$('#reading-graph-year-toggles').hide();
		$('#history_graph_container').empty();

	} else {
		$('#reading-history-details').hide();
		request_graph_data(value);
	}
})

$('.reading-graph-checkbox').change(function() {
	var checkbox_name = $(this).attr('name');
	var checkbox_value = $(this).is(':checked');

	if (checkbox_name == 'all') {
		$('.reading-graph-checkbox').each(function() {
			$checkbox = $(this)
			if ($checkbox.attr('name') != 'all' && $checkbox.is(':checked') != checkbox_value) {
				$(this).click()
			}
		})

		return;
	}

	var display_value = checkbox_value ? 'inline' : 'none';
	$('head').append('<style>.line-' + checkbox_name + '{display: ' + display_value + ';}</style>')
});

function update_details_div() {
	var year = $("#reading-year").val()
	
	data = {
		'year': year
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/history_year_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$container = $('#history-year-container')
			$container.empty()
			$container.html(response['html'])
		}
	})
}

function request_graph_data(graph_type) {
	$.ajax({
		"type": "POST",
		"url": "/reading/" + graph_type + "_graph_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			create_graph(response, graph_type);
			$('#reading-graph-year-toggles').show();
		}
	});
}

var line_colors = ['red', 'blue', 'green', 'yellow']
var active_node = false

d3.selection.prototype.moveToBack = function() {  
        return this.each(function() { 
            var firstChild = this.parentNode.firstChild; 
            if (firstChild) { 
                this.parentNode.insertBefore(this, firstChild); 
            } 
        });
    };

function create_graph(data, graph_type) {
	console.log(data)

	var close_button;

	$('svg').remove()

	var margin = {top: 10, right: 30, bottom: 170, left: 90};
	var width = $('.main_container').width() - margin.left - margin.right;
	var height = $(window).height() - margin.top - margin.bottom
	
	var min_x = 0;
	var max_x = 366;

	var min_y = 0
	var max_y = d3.max(data, function(array) {
		return d3.max(array['values']);
	})

	var x = d3.scaleLinear()
			.domain([min_x, max_x])
			.range([0, width]);

	var y = d3.scaleLinear()
		.domain([min_y, max_y])
		.range([height, 0])
		.nice();

	var svg = d3.select('#history_graph_container').append('svg')
				.attr('width', width)
				.attr('height', height)
			.append('g')
				.attr('transform', 'translate(' + margin.left + ',' + margin.top +')');


	var max_y_values = get_max_y_values(data)

	function mouseover() {
		svg.selectAll('.focus_circle')
			.style('opacity', 1);

		svg.selectAll('.focus_text')
			.style('opacity', 1);

		svg.selectAll('.focus_line')
			.style('opacity', 1);

		svg.selectAll('.focus_date')
			.style('opacity', 1);		
	}

	function mousemove() {
		var mouse = this
		var x0 = x.invert(d3.mouse(this)[0]);

		svg.selectAll('.focus_circle')
			.attr('cx', x(x0))
			.attr('cy', function(d) {
				return y(find_y_value(d, mouse, 'values'));
			})


		var x1 = x(x0)
		var x2 = x(x0)

		var y1 = y(max_y_values[Math.round(x0)]) + 5
		var y2 = y(0)

		svg.selectAll('.focus_line')
			.attr('x1', x1)
			.attr('x2', x2)
			.attr('y1', y1)
			.attr('y2', y2)


		svg.selectAll('.focus_text')
			.attr('x', x(x0 + 2))
			.attr('y', function(d) {
				return y(find_y_value(d, mouse, 'values')) - 4;
			})
			.text(function(d) {
				return msToTime(find_y_value(d, mouse, 'values'));
			})


		svg.selectAll('.focus_date').filter(function(d, i) { return i == 0; })
			.attr('x', x(x0) - 20)
			.attr('y', y(0) + 30)
			.text(function(d) {
				var x0 = x.invert(d3.mouse(mouse)[0]);
				var day_number = Math.round(x0);

				var first_day = new Date()
				first_day.setFullYear(2020) // We use 2020 since it is a leap year.
				first_day.setMonth(0)
				first_day.setDate(1)

				var target_date = first_day;
				target_date.setDate(first_day.getDate() + day_number);

				var date_parts = target_date.toString().split(" ")

				return date_parts[2] + ' ' + date_parts[1];
			});


	}

	function mouseout() {
		svg.selectAll('.focus_circle')
			.style('opacity', 0);

		svg.selectAll('.focus_text')
			.style('opacity', 0);

		svg.selectAll('.focus_line')
			.style('opacity', 0)

		svg.selectAll('.focus_date')
			.style('opacity', 0);
	}


	function find_y_value(d, mouse, name) {
		var x0 = x.invert(d3.mouse(mouse)[0]);
		var i = Math.round(x0);
		var values = d[name];
		var y0 = d[name][i]

		if (typeof y0 == 'undefined') {
			var length = d[name].length
			y0 = d[name][length-1]
		}

		return y0;
	}
	


	var graph_elements = svg.selectAll('g')
		.data(data)
		.enter()
			.append('g')
			.selectAll('line')
			.data(function(d, i) {
				formatted_data = []

				for(var j = 0; j < d['values'].length; j++) {
					formatted_data.push({
						// 'line_number': i,
						'year': d['year'],
						'value': d['values'][j]
					})
				}

				return formatted_data
			})

	var line = d3.line()
				.x(function(d, i){
					return x(i)
				})
				.y(function(d, i) {
					return y(d)
				});
				//.curve(d3.curveMonotoneX)

	var node_number = 0
	for (var i = data.length-1; i >= 0; i--) {
		var year = data[i]['year'];

		var path = svg.append('path')
			.data([data[i]['values']])
			.attr('class', 'line')
			.attr('class', 'graph_line line-' + year)
			//.attr('id', 'line-' + data[i]['year'])
			.attr('d', line)
			.attr('stroke', line_colors[i]);

			if (graph_type == 'books_completed') {
				var completion_info = data[i]['completion_info']
				var completion_number = 0
				for (var j = 0; j <= completion_info.length-1; j++) {
					completion_number++;

					var tooltip_text = "<strong>" + completion_info[j]['title'] + "</strong><br/>Completed: " + completion_info[j]['date'];

					var tip = d3.tip()
						.attr('class', 'd3-tip')
						.offset([-8, 0])
						.html(tooltip_text);

					svg.call(tip)

					node_number++;

					var dot = svg.append('circle')
						.attr('cx', x(completion_info[j]['day_number']))
						.attr('cy', y(completion_number))
						.attr('r', 4.5)
						.attr('fill', line_colors[i])
						.attr('class', 'readthrough-data-point line-' + year)
						.attr('id', 'node-' + node_number)
						.attr('data-id', completion_info[j]['readthrough_id'])
						.attr('data-node-number', node_number)
						.on('mouseover', tip.show)
						.on('mouseout', tip.hide)
						.on('click', function(d, i) {

							close_readthrough_details(svg, active_node)

							window.current_node = $(this).data('node-number')
							var readthrough_id = $(this).data('id')
							
							if (active_node) {
								d3.select(active_node).style("r", 4.5);
								d3.select(active_node).style("stroke", "none");
								d3.select(active_node).style("stroke-width", 0);
							}
							active_node = this

							data = {
								'readthrough_id': readthrough_id
							}

							$.ajax({
								"type": "POST",
								"url": "/reading/load_single_readthrough",
								"contentType": "application/json",
								"dataType": "json",
								"data": JSON.stringify(data),
								success: function(response) {

									var title_length = response['book_title'].length;
									var safe_title_length = 30;
									var title_overlength = d3.max([title_length - safe_title_length, 0]) * 3

									var x = 90
									var y = 0
									var width = 650 + title_overlength
									var height = 340

									var background = svg.append('rect')
										.attr('x', x-2)
										.attr('y', y-2)
										.attr('width', width+4)
										.attr('height', height+4)
										.attr('fill', 'black')
										.attr('class', 'readthrough-background');

									var fo = svg.append('foreignObject')
										.attr('x', x)
										.attr('y', y)
										.attr('width', width)
										.attr('height', height)
										.html(response['html'])

									var close_button = svg.append('text')
										.html('&#x2715;')
										.attr('x', x + width - 20)
										.attr('y', y + 15)
										.attr('class', 'graph-readthrough-close')
										.on('click', function() {
											close_readthrough_details(svg, active_node)
										})

									//d3.select('foreignObject').moveToBack();
									d3.select(active_node).style("r", 10);
									d3.select(active_node).style("stroke", "black");
									d3.select(active_node).style("stroke-width", 4);
								}
							})

						});
				}
			}
	}
	window.max_node_number = node_number

	// Add dotted line to continue past present day.
	var recent_year_length = data[0]['values'].length
	if (recent_year_length < 366) {

		var x1 = x(recent_year_length - 1)
		var x2 = x(366)

		var y1 = y(data[0]['values'][recent_year_length-1]);
		var y2 = y1

		var line = svg.append('line')
			.attr("x1", x1)
			.attr("y1", y1)
			.attr("x2", x2)
			.attr("y2", y2)
			.attr("stroke", line_colors[0])
			.style("stroke-dasharray", ("3, 3"))
			.attr("stroke-width", 2)
			.attr('class', 'line-' + data[0]['year']);
	}

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.ticks(12)
			.tickFormat(function(d, i) {
				return data[1]['dates'][d]
			})
		);

	svg.append('g')
		.call(
			d3.axisLeft(y)
			.tickFormat(function(d, i) {
				if (graph_type == 'books_completed') {
					return d;
				} else if (graph_type == 'reading_time') {
					return msToTime(d);
				}
			})
		);


	svg.selectAll('myLegendDots')
		.data(data)
		.enter()
			.append('rect')
			.attr('x', 20)
			.attr('y', function(d, i) {
				return i * 20;
			})
			.attr('width', 12)
			.attr('height', 12)
			.attr('class', function(d, i) {
				return 'line-' + d['year'];
			})
			.style('fill', function(d, i) {
				return line_colors[i]
			});

	svg.selectAll('myLegendLabels')
		.data(data)
		.enter()
			.append('text')
			.attr('x', 40)
			.attr('y', function(d, i) {
				return (i*20) + 11;
			})
			.attr('class', function(d, i) {
				return 'line-' + d['year'];
			})
			.text(function(d, i) {
				return d['year']
			});

	// x-axis label
	svg.append("text")             
		.attr("transform",
			"translate(" + (width/2) + " ," + 
				(height + margin.top + 30) + ")")
		.style("text-anchor", "middle")
		.text('Date');

	// y-axis label
	svg.append("text")
		.attr("transform", "rotate(-90)")
		.attr("y", 0 - margin.left)
		.attr("x",0 - (height / 2))
		.attr("dy", "1em")
		.style("text-anchor", "middle")
		.text(function() {
			if (graph_type == 'reading_time') {
				return 'Reading Time'
			} else if (graph_type == 'books_completed') {
				return 'Books Completed'
			}
		});

	var focus_line = svg.selectAll('focus_line')
		.data(data)
		.enter()
		.append('line')
			.attr('class', 'focus_line')
			.style('opacity', 0)
			.style('stroke', 'black')
			.style('stroke-width', 2);

	var focus = svg.selectAll('focus_circle')
		.data(data)
		.enter()
		.append('circle')
			.style('fill', function(d, i) {
				return line_colors[i]

			})
			.attr('class', 'focus_circle')
			.attr('r', 5)
			.style('opacity', 0);

	var focus_text = svg.selectAll('focus_text')
		.data(data)
		.enter()
		.append('text')
			.attr('class', 'focus_text')
			.style('opacity', 0);

	var focus_date = svg.selectAll('focus_date')
		.data(data)
		.enter()
		.append('text')
			.attr('class', 'focus_date')
			.style('opacity', 0);

	if (graph_type == 'reading_time') {
		svg.append('rect')
			.style("fill", "none")
			.style("pointer-events", "all")
			.attr('width', width)
			.attr('height', height)
			.on('mouseover', mouseover)
			.on('mousemove', mousemove)
			.on('mouseout', mouseout);
	}


}

function close_readthrough_details(svg, active_node) {
	svg.selectAll("foreignObject").remove();
	svg.selectAll(".readthrough-background").remove();
	svg.selectAll(".graph-readthrough-close").remove();
	window.current_node = false;

	if (active_node) {
		d3.select(active_node).style("r", 4.5);
		d3.select(active_node).style("stroke", "none");
		d3.select(active_node).style("stroke-width", 0);
	}
}

// Get the highest y value for any given x value.
function get_max_y_values(data) {
	var max_y_values = []
	for (var i = 0; i <= 366; i++) {
		var max = 0
		for (var j = data.length - 1; j >= 0; j--) {
			var value = data[j]['values'][i]

			if (!value) {
				value = max_y_values[max_y_values.length - 1]
			}

			if (value > max) {
				max = value
			}
		}

		max_y_values.push(max)
	}

	return max_y_values;	
}

function msToTime(duration) {
    var hours = Math.floor((duration / (1000 * 60 * 60)) % 24);
    var days = Math.floor((duration / (1000 * 60 * 60 * 24)))

    return days + 'd ' + hours + 'h';
}