$(document).ready(function() {
	update_details_div();
})

$('#reading-year').change(function() {
	update_details_div()
});

$('input[type=radio][name=history_type]').change(function() {
	var value = $(this).val();

	if (value == 'details') {
		$('#reading-history-details').show()
		$('#history_graph_container').empty()

	} else if (value == 'books_completed') {
		$('#reading-history-details').hide()
		request_books_completed_graph()

	} else if (value == 'reading_time') {
		$('#reading-history-details').hide()
		request_reading_time_graph()
	}
})

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
			console.log(response)
			$container = $('#history-year-container')
			$container.empty()
			$container.html(response['html'])
		}
	})
}

function request_books_completed_graph() {
	$.ajax({
		"type": "POST",
		"url": "/reading/books_completed_graph_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			create_graph(response)
		}
	});
}

function request_reading_time_graph() {
	$.ajax({
		"type": "POST",
		"url": "/reading/reading_time_graph_data",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			create_graph(response)
			console.log(response)
		}
	});
}

var line_colors = ['red', 'blue', 'green', 'yellow']

function create_graph(data) {
	console.log(data)

	$('svg').remove()

	var margin = {top: 10, right: 30, bottom: 150, left: 90};
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

	for (var i = 0; i <= data.length - 1; i++) {
			var path = svg.append('path')
				.data([data[i]['values']])
				.attr('class', 'line')
				.attr('class', 'graph_line')
				.attr('id', data[i]['year'] + '-line')
				.attr('d', line)
				.attr('stroke', line_colors[i])
	}

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.ticks(12)
			// .tickValues(get_x_tick_values(data, width))
			.tickFormat(function(d, i) {
				return data[1]['dates'][d]
			})
		);

	svg.append('g')
		.call(
			d3.axisLeft(y)
			//.tickFormat(d => format_y_value(d))
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
		.attr("y", 30 - margin.left)
		.attr("x",0 - (height / 2))
		.attr("dy", "1em")
		.style("text-anchor", "middle")
		.text('Books Completed');

}