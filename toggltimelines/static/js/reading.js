$('.new-readthrough-btn').on('click', function() {
	$(this).siblings('.new-readthrough-control').show()
})

$('.create-readthrough-btn').on('click', function() {

	readthrough_data = $(this).closest('.book-control').serializeArray().reduce(function(obj, item) {
	    obj[item.name] = item.value;
	    return obj;
	}, {});



	$.ajax({
		"type": "POST",
		"url": "/reading/new_readthrough",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(readthrough_data),
		success: function(response) {
			console.log(response)
		}
	})
})