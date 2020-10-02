

$("#sync-form").submit(function(e) {
	e.preventDefault();

	var data = $(this).serializeArray().reduce(function(obj, item) {
	    obj[item.name] = item.value;
	    return obj;
	}, {});

	$.ajax({
		"type": "POST",
		"url": "/sync/run_sync",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		'beforeSend': function() {
				$('#sync-start-btn').hide();
				$('#loading_div').show();	
			},
			'complete': function() {
				$('#loading_div').hide();
			},
		success: function(response) {
			console.log(response)

			$('#sync-complete-message').text(response['message'])
		}
	})
})