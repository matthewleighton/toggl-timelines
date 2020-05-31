$(document).ready(function() {
	//create_frequency_graph()

	$.ajax({
		"type": "POST",
		"url": "/frequency_data",
		"contentType": "application/json",
		"dataType": "json",
		//"data": JSON.stringify(serialized_data),
		success: function(response) {
			console.log(response)
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

function make_y_gridlines(y) {
	return d3.axisLeft(y)
		.ticks(5)
}

function make_x_gridlines(x) {
	return d3.axisBottom(x)
		.ticks(60)
}

function create_frequency_graph(data) {
    console.log('create_frequency_graph')
    console.log(data)
    $('svg').remove()

    var margin = {top: 10, right: 30, bottom: 30, left: 60};

	var width = $('#graph_container').width() - margin.left - margin.right;
	//var width = 1600
	//var height = 900
	var height = $(window).height() - 100 - margin.top - margin.bottom;

	var max_time = 1439
	var min_time = 0

	//var max_frequency = d3.max(data, function(d) {console.log(d); return d})
	var max_frequency = d3.max(data.all)
	var min_frequency = 0
	
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
					.x(function(d, i){console.log(i);return x(i)})
					.y(function(d){return y(d)});

	svg.append('path')
		.data([data.all])
		.attr('class', 'line')
		.attr('d', line)

	svg.append('g')
		.attr('transform', 'translate(0,' + height + ')')
		.call(
			d3.axisBottom(x)
			.tickValues(get_x_tick_values())
			.tickFormat(d => get_x_tick_format(d))
		);
	
	svg.append('g')
		.call(d3.axisLeft(y));

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