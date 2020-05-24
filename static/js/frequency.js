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

function create_frequency_graph() {
    console.log('create_frequency_graph')
    $('svg').remove()

    

    
}