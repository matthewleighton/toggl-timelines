$('.new-readthrough-btn').on('click', function() {
	$(this).siblings('.new-readthrough-control').show()
})



var search_timeout = false
$('#new-readthrough-search').on('input', function() {
	var title = this.value.toLowerCase()

	if (search_timeout) {
		clearTimeout(search_timeout)
	}

	search_timeout = setTimeout(function() {
		search_books(title)
	},
	600)
})

function search_books(title) {
	title = title.trim()

	if (!title) {
		$('.books-search-results').empty()
		return
	}

	data = {
		'title': title
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/search_books",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$container = $('.books-search-results')
			$container.replaceWith(response)
		}
	})
}


$('body').on('click', '.readthrough-complete-checkbox', function() {
	var $parent_container = $(this).closest('.new-readthrough-control');
	var $end_container = $parent_container.find('.new-readthrough-end-date');

	if ($(this).is(':checked')) {
		$end_container.css('display', 'flex');
	} else {
		$end_container.hide();
	}
})

$('body').on('change', 'input[type=radio][name=book_format]', function() {
	var $parent_container = $(this).closest('.new-readthrough-control');
	var $page_container = $parent_container.find('.new-readthrough-pages')

	if (this.value == 'physical') {
		$page_container.css('display', 'flex')
	} else {
		$page_container.hide()
	}
})







$('body').on('click', '.create-readthrough-btn', function() {

	var $parent_container = $(this).closest('.new-readthrough-control');
	$parent_container.find('input').removeClass('error-field')
	$results_container = $(this).closest('.books-search-results');

	var data = $(this).closest('.book-control').serializeArray().reduce(function(obj, item) {
	    obj[item.name] = item.value;
	    return obj;
	}, {});

	var validation_error = false;

	if (data['book_format'] == 'physical' && !data['first_page']) {
		var $first_page_input = $parent_container.find('input[name="first_page"]');
		$first_page_input.addClass('error-field');
		validation_error = true;
	}

	if (data['book_format'] == 'physical' && !data['last_page']) {
		var $last_page_input = $parent_container.find('input[name="last_page"]');
		$last_page_input.addClass('error-field');
		validation_error = true;
	}

	if (!data['start_date']) {
		var $start_date_input = $parent_container.find('input[name="start_date"]')
		$start_date_input.addClass('error-field');
		validation_error = true;
	}

	if (data['readthrough_complete'] && !data['end_date']) {
		var $end_date_input = $parent_container.find('input[name="end_date"]');
		$end_date_input.addClass('error-field');
		validation_error = true;
	}

	if (data['start_date'] && data['end_date'] && data['start_date'] > data['end_date']) {
		var $start_date_input = $parent_container.find('input[name="start_date"]');
		var $end_date_input = $parent_container.find('input[name="end_date"]');
		$start_date_input.addClass('error-field');
		$end_date_input.addClass('error-field');
	}

	if (validation_error) {
		return
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/new_readthrough",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$results_container.empty()
			$(response).insertAfter($results_container)

			setTimeout(function() {
				$('.new-readthrough-success').fadeOut(500)
			},
			3000)
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
		case 'update_daily_reading_goal':
			var input_type = 'number';
			var input_class = 'hidden-number-input';
			var input_value = $el.attr('data-minutes')
			break;
		case 'update_start_date':
		case 'update_end_date':
		case 'update_target_end_date':
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


$('body').on('click', '.delete-readthrough-btn', function() {
	var readthrough_id = $(this).attr('data-id')
	var title = $(this).attr('data-title')
	var message = `Delete readthrough for "${title}"?`
	var $readthrough_element = $(this).closest('.readthrough-control')

	console.log($readthrough_element)

	user_confirmation = confirm(message)

	if (user_confirmation) {
		delete_readthrough(readthrough_id, $readthrough_element)
	}
})

function delete_readthrough(readthrough_id, readthrough_element) {
	data = {
		'readthrough_id': readthrough_id
	}

	readthrough_element.remove()

	$.ajax({
			"type": "POST",
			"url": "/reading/delete_readthrough",
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify(data),
			success: function(response) {
				$readthrough_element.remove()
			}
		})
}