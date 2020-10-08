var current_node = false
var max_node_number = 1

$(document).ready(function() {
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

	// var background = svg.append("rect")
	// 	.attr('class', 'svg-background')
	//     .attr("width", "100%")
	//     .attr("height", "100%")
	//     .attr("fill", "#f5f5f5");

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
				})
				.curve(d3.curveMonotoneX)

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
						.attr('cx', x(completion_info[j]['day_number']) + 5)
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

function msToTime(duration) {
    var hours = Math.floor((duration / (1000 * 60 * 60)) % 24);
    var days = Math.floor((duration / (1000 * 60 * 60 * 24)))

    return days + 'd ' + hours + 'h';
}