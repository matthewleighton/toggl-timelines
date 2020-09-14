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

$('body').on('click', '.hidden-input', function() {
	var $el = $(this);
	var original_value = $el.text()

	var $container = $el.closest('.readthrough-control');
	var readthrough_id = $container.attr('data-id');
	var endpoint = $el.attr('data-endpoint')

	switch(endpoint) {
		case 'update_position':
			var input_type = 'number';
			var input_class = 'hidden-number-input';
			var input_value = original_value
			break;
		case 'update_start_date':
		case 'update_end_date':
			var input_type = 'date';
			var input_class = 'hidden-date-input';
			var input_value = $el.attr('data-date')
			break;
	}

	var $input = $(`<input type="${input_type}" class="${input_class}"/>`).val( input_value );
	$el.replaceWith( $input );
	$input.select();

	var save = function(){
	    var new_value = $input.val()

	    if (new_value == original_value || new_value == input_value) {
	    	
	    	$input.replaceWith( $el );
	    	$el.text(original_value)	

	    	return;	
	    }

	    var data = {
	    	readthrough_id: readthrough_id,
	    	value: new_value,
	    	endpoint: endpoint
	    }

	    $.ajax({
			"type": "POST",
			"url": "/reading/" + endpoint,
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify(data),
			success: function(response) {
				// TODO: Some kind of validation. Only replace if True.
				$container.replaceWith(response)
			}
		})
	};

	$input.one('blur', save).focus();
});