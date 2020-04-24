$(document).ready(function() {
	
	$( "#comparison_form" ).on( "submit", function( event ) {
		
		event.preventDefault();

		serialized_data = $( this ).serializeArray();
		serialized_data = format_serialized_data(serialized_data);

		$.ajax({
			"type": "POST",
			"url": "/comparison_data",
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify(serialized_data),
			success: function(response) {
				create_graph(response)				
			}
		})
	});

	$('#comparison_form').change(function() {
		$('#comparison_form').submit()
	});

	$('#comparison_form').submit()
})

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


function format_percentage(ratio) {
	value = Math.round(ratio*100) - 100

	if (value == 9900) {
		return "∞"
	}

	sign = Math.sign(value) > 0 ? '+' : '-'

	return sign + Math.abs(Math.round(ratio*100) - 100) + '%'
}

function format_seconds(seconds) {
	var timestamp = 9462;

	var hours = Math.floor(seconds / 60 / 60);
	var minutes = Math.floor(seconds / 60) - (hours * 60);
	var seconds = Math.floor(seconds % 60);

	var hours_label = (hours == 1) ? " hour, " : " hours, "
	var minutes_label = (minutes == 1) ? " minute, " : " minutes, "
	var seconds_label = (minutes == 1) ? " second " : " seconds "

	return_string = ""

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
		return_string = "0 seconds"
	}

	return return_string

	return hours + hours_label + minutes + minutes_label + seconds + seconds_label
}

function get_current_period_string() {
	var current_period_number = $('#timeframe').val();
	switch (current_period_number) {
		case '1':
			return 'Today: '
			break
		case '7':
			return 'Past 7 days: '
			break
		case '30':
			return 'Past 30 days: '
			break
		case '365':
			return 'Past 365 days: '
			break
	}

	return 'This period: '
}

function get_average_label() {
	var current_period_number = $('#timeframe').val();
	var comparison_period_number = $('#datarange').val();

	console.log(current_period_number)
	console.log(comparison_period_number)

	if (current_period_number !== comparison_period_number) {
		return "Average: ";
	}

	switch (current_period_number) {
		case '1':
			return 'Yesterday: '
			break
		case '7':
			return 'Previous 7 days: '
			break
		case '30':
			return 'Previous 30 days: '
			break
		case '365':
			return 'Previous 365 days: '
			break
	}

	return 'Average: '
}

function create_graph(data) {
	console.log(data)
	
	$('svg').remove()
	$('.d3-tip').remove()

	var width = $('#graph_container').width()
	var half_width = width/2
	var margin = ({top: 30, right: 60, bottom: 10, left: 60})
	var bar_height = 35
	var height = Math.ceil((data.length + 0.1) * bar_height) + margin.top + margin.bottom
	var tooltip = d3.select("body").append("div").attr("class", "toolTip");

	var current_period_string = get_current_period_string()
	

	/*
	var x_position = d3.scaleLinear()
					.domain(d3.extent(data, d => d.ratio))
					.rangeRound([margin.left, width - margin.right]);
	*/

	var x_position = d3.scalePow()
					.exponent(0.6)
					.domain([0, 3])
					//.domain(d3.extent(data, d => d.ratio))
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



	metric = 'relative'
	format = d3.format(metric === "absolute" ? "+,d" : "+,.0%")
	tickFormat = metric === "absolute" ? d3.formatPrefix("+.1", 1e6) : format

	yAxis = g => g
    .attr("transform", `translate(${x_position(0)},0)`)
    .call(d3.axisLeft(y_position).tickFormat(i => data[i].name).tickSize(0).tickPadding(6))
    .call(g => g.selectAll(".tick text").filter(i => data[i].ratio < 0)
        .attr("text-anchor", "start")
        .attr("x", 6))

    xAxis = g => g
    	.attr("transform", `translate(0,${margin.top})`)
    	.call(d3.axisTop(x_position).ticks(width / 80).tickFormat(tickFormat))
    	.call(g => g.select(".domain").remove())

    /*
    canvas.append("g")
    	.call(yAxis);
	*/

    canvas.append("g")
    	.call(xAxis);

    var tip = d3.tip()
	  .attr('class', 'd3-tip')
	  .offset([-10, 0])
	  .html(function(d) {
	    current_tracked = format_seconds(d.current_tracked)
	    average = format_seconds(d.average)

	    average_label = get_average_label()

	    difference_seconds = Math.abs(d.average - d.current_tracked)
	    difference_string = format_seconds(difference_seconds)

	    return "<strong>" + d.name + "</strong><div><span>" + current_period_string + "</span>" + current_tracked + "</div><div><span>" + average_label + "</span>" + average + "</div><div><span>Difference: </span>" + difference_string + "</div>";
	    //return "<strong>Frequency:</strong> <span style='color:red'>" + d.frequency + "</span>";
	  })

	canvas.call(tip)




	canvas.append("g")
		.selectAll("rect")
		.data(data)
		.join("rect")
			.attr("fill", d => d.color)
			.attr("x", d => x_position(Math.min(d.ratio, 1)))
			.attr("y", (d, i) => y_position(i))
			.attr("width", d => Math.abs(x_position(d.ratio) - x_position(1)))
			.attr("height", y_position.bandwidth())
			.on('mouseover', tip.show)
      		.on('mouseout', tip.hide)
			
	
	canvas.append("g")
		.attr("font-family", "sans-serif")
		.attr("font-size", 10)
		.selectAll("text")
		.data(data)
		.join("text")
			.attr("text-anchor", d => d.ratio < 1 ? "end" : "start")
			.attr("x", d => x_position(d.ratio) + Math.sign(d.ratio - 1) * 4)
			.attr("y", (d, i) => y_position(i) + y_position.bandwidth() / 2)
			.attr("dy", "0.35em")
			//.text(format_percentage(d.ratio))
			.text(d => format_percentage(d.ratio))
			//.text(d => Math.abs(Math.round(d.ratio*100) - 100) + '%')

	

	

}


