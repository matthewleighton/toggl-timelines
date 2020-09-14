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
	var original_position = $el.text()

	var $container = $el.closest('.readthrough-control');
	var readthrough_id = $container.attr('data-id');

	var $input = $('<input type="number" class="current-readthrough-position-input"/>').val( original_position );
	$el.replaceWith( $input );
	$input.select();

	var save = function(){
	    var new_position = $input.val()

	    var $p = $('<span class="hidden-input" />').text( new_position );
	    $input.replaceWith( $p );

	    if (new_position == original_position) return;

	    var data = {
	    	readthrough_id: readthrough_id,
	    	position: new_position
	    }

	    $.ajax({
			"type": "POST",
			"url": "/reading/update_position",
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