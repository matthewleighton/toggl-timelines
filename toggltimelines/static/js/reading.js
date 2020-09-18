$('.new-readthrough-btn').on('click', function() {
	$(this).siblings('.new-readthrough-control').show()
})

/* Trigger hidden field submission by pressing Enter. */
$('body').keypress(function(e) {
	if (e.which == 13) {
		var $focused = $(':focus');
		$focused.blur()
	}
})


/* New Readthrough search */
var book_search_timeout = false
$('#new-readthrough-search').on('input', function() {
	var title = this.value.toLowerCase()

	if (book_search_timeout) {
		clearTimeout(book_search_timeout)
	}

	book_search_timeout = setTimeout(function() {
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


/* Hiding/showing fields in new readthrough creation */
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






/* Creating new readthroughs */
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
			$('#new-readthrough-search').val('')

			if (response['reload_active_readthroughs']) {
				$('.active-readthroughs').html(response['html'])
			}
		}
	})
})



/* Hidden input fields on readthrough display */
$('body').on('click', '.hidden-input', function() {
	var $el = $(this);
	var original_value = $el.text()

	var $parent = $el.closest('.readthrough-control');

	var $container = $el.closest('.readthrough-control');
	var readthrough_id = $container.attr('data-id');

	var $readthrough_fields = $container.find('.readthrough-fields')
	var $readthrough_position = $container.find('.readthrough-position')

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
				console.log(response)
				$readthrough_fields.replaceWith(response['readthrough_fields'])
				$readthrough_position.replaceWith(response['readthrough_position'])
			}
		})
	};

	$input.one('blur', save).focus();
});


/* Deleting readthroughs */
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


/* Loading additional past readthroughs */
var number_loaded = 0
$('.load-past-readthroughs').click(function(e) {
	e.preventDefault();

	data = {
		'number_loaded': number_loaded
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/load_past_readthroughs",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			number_loaded += response['amount_per_request'];

			$('#previously-read-header').show();
			$('.load-past-readthroughs').text('Load more')

			$('#past-readthrough-loading-results').append(response['html'])

			if (response['none_remaining']) {
				$('.load-past-readthroughs').hide()
			}
		}
	})

})



/* Searching past readthroughs */
var readthrough_search_timeout = false
$('body').on('input', '#past-readthrough-search', function() {
	var title = this.value.toLowerCase()

	if (readthrough_search_timeout) {
		clearTimeout(readthrough_search_timeout)
	}

	readthrough_search_timeout = setTimeout(function() {
		search_readthroughs(title)
	},
	600)
})

function search_readthroughs(title) {
	title = title.trim()

	if (!title) {
		$('#past-readthrough-search-results').hide()
		$('#past-readthrough-loading-results').show()
		return
	}

	data = {
		'title': title
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/search_readthroughs",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			$('#past-readthrough-loading-results').hide()
			$('#past-readthrough-serach-results').show()
			$('#past-readthrough-search-results').html(response)
		}
	})

}



/* Updating book covers */
$('body').on('click', '.readthrough-image img', function() {
	$cover_image = $(this)
	$cover_image.css('opacity', 0);
	$cover_image.css('cursor', 'default');
	$cover_image.css('pointer-events', 'none')

	var $parent_container = $(this).closest('.readthrough-image');
	var $cover_input = $parent_container.find('.readthrough-cover-input');

	$cover_input.show();
	$cover_input.focus();
})

$('body').on('blur', '.readthrough-cover-input', function() {
	var $cover_input = $(this)
	var $parent_container = $(this).closest('.readthrough-image');
	var $cover_image = $parent_container.find('img')

	cover_url = $cover_input.val()

	user_confirmation = false
	if (cover_url) {
		user_confirmation = confirm('Update cover?')
	}

	if (user_confirmation) {
		book_id = $cover_input.attr('data-book-id');
		readthrough_id = $cover_input.attr('data-readthrough-id');

		data = {
			'book_id': book_id,
			'readthrough_id': readthrough_id,
			'cover_url': cover_url
		}

		$.ajax({
			"type": "POST",
			"url": "/reading/update_cover",
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify(data),
			success: function(response) {
				$parent_container = $cover_input.closest('.readthrough-control')
				$parent_container.replaceWith(response)
			}
		})
	}

	$cover_input.val('')
	$cover_input.hide();
	$cover_image.css('opacity', 1)
	$cover_image.css('cursor', 'pointer')
	$cover_image.css('pointer-events', 'auto')
})

$('.reading-reload').click(function() {
	$.ajax({
		"type": "POST",
		"url": "/reading/toggl_sync",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(),
		success: function(response) {
			$active_readthroughs_div = $('.active-readthroughs')
			$active_readthroughs_div.replaceWith(response['html'])
		}
	})
})

/* Start tracking */
$('body').on('click', '.start-track', function() {
	
	console.log('Clicked start track button.')

	$button = $(this)
	readthrough_id = $button.attr('data-id')

	data = {
		'readthrough_id': readthrough_id
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/start_track",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			console.log(response)

			$button.removeClass('start-track')
			$button.removeClass('btn-success')

			$button.addClass('stop-track')
			$button.addClass('btn-danger')
			$button.html('&#9632;') // Stop sign
		}
	})
})

/* Stop tracking */

$('body').on('click', '.stop-track', function() {

	$button = $(this)
	readthrough_id = $button.attr('data-id')

	data = {
		'readthrough_id': readthrough_id
	}

	$.ajax({
		"type": "POST",
		"url": "/reading/stop_track",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			console.log(response)

			$button.removeClass('stop-track')
			$button.removeClass('btn-danger')

			$button.addClass('start-track')
			$button.addClass('btn-success')
			$button.html('&#9658;') // Stop sign
		}
	})
})