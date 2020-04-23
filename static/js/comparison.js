$(document).ready(function() {
	$.ajax($SCRIPT_ROOT + '/comparison_data').done(function(data) {
		create_graph(data)		
	})

	$( "#comparison_form" ).on( "submit", function( event ) {
		event.preventDefault();
		console.log( $( this ).serialize() );
	});

	
})


/*
	var circle = canvas.append("circle")
				.attr("cx", 250)
				.attr("cy", 250)
				.attr("r", 50)
				.attr("fill", "red");

	var rect = canvas.append("rect")
				.attr("width", 100)
				.attr("height", 50)

	var line = canvas.append("line")
				.attr("x1", 0)
				.attr("y1", 100)
				.attr("x2", 400)
				.attr("y2", 400)
				.attr("stroke", "green")
				.attr("stroke-width", 10);
	*/

function create_graph(data) {

	/*
	data = [
		{
			'name': 'Coding',
			'value': 2.1
		},
		{
			'name': 'Reading',
			'value': 0.4
		},
		{
			'name': 'Johanna',
			'value': 1
		},
		{
			'name': 'Physics',
			'value': 1.5
		},
		{
			'name': 'Video Games',
			'value': 0.1
		}
	]
	*/
	
	console.log(data)

	var width = $('#graph_container').width()

	console.log(width)
	
	var half_width = width/2

	var margin = ({top: 30, right: 60, bottom: 10, left: 60})
	
	var bar_height = 25

	var height = Math.ceil((data.length + 0.1) * bar_height) + margin.top + margin.bottom




	/*
	var x_position = d3.scaleLinear()
					.domain(d3.extent(data, d => d.value))
					.rangeRound([margin.left, width - margin.right]);
	*/

	var x_position = d3.scalePow()
					.exponent(0.6)
					.domain([0, 3])
					//.domain(d3.extent(data, d => d.value))
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


	/*
	canvas.append("rect")
    	.attr("width", "100%")
    	.attr("height", "100%")
    	.attr("fill", "pink");
	*/


	metric = 'relative'
	format = d3.format(metric === "absolute" ? "+,d" : "+,.0%")
	tickFormat = metric === "absolute" ? d3.formatPrefix("+.1", 1e6) : format

	yAxis = g => g
    .attr("transform", `translate(${x_position(0)},0)`)
    .call(d3.axisLeft(y_position).tickFormat(i => data[i].name).tickSize(0).tickPadding(6))
    .call(g => g.selectAll(".tick text").filter(i => data[i].value < 0)
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




	canvas.append("g")
		.selectAll("rect")
		.data(data)
		.join("rect")
			//.attr("fill", d => d3.schemeSet1[d.value > 1 ? 1 : 0])
			.attr("fill", d => d.color)
			.attr("x", d => x_position(Math.min(d.value, 1)))
			.attr("y", (d, i) => y_position(i))
			.attr("width", d => Math.abs(x_position(d.value) - x_position(1)))
			.attr("height", y_position.bandwidth());
			
	
	canvas.append("g")
		.attr("font-family", "sans-serif")
		.attr("font-size", 10)
		.selectAll("text")
		.data(data)
		.join("text")
			.attr("text-anchor", d => d.value < 1 ? "end" : "start")
			.attr("x", d => x_position(d.value) + Math.sign(d.value - 1) * 4)
			.attr("y", (d, i) => y_position(i) + y_position.bandwidth() / 2)
			.attr("dy", "0.35em")
			.text(d => Math.round(d.value*100) + '%')
			//.text(d => d.value)

	

	

}

