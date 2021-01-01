var start_days_ago = 14
var end_days_ago = 7
var disable_search = false

var filter_settings = {
	'active': false,
	'type': false,
	'value': false
}

function get_day_percentage() {
	var now  = new Date();
	var hour = now.getHours();
	var minute = now.getMinutes();

	minutes_since_midnight = hour * 60 + minute	
	day_percentage = (minutes_since_midnight/(60*24))*100

	return day_percentage
}

function activate_client_mode(value) {
	mode = (value) ? 'client' : 'project'

	$('.tracked_time').each(function() {
		hex_code = $(this).data(mode + '-hex')
		$(this).css('background-color', hex_code)
	})
}

function activate_stack_mode(value) {
	display = (value) ? 'none' : 'block'
	border_radius = (value) ? '0px' : '3px'

	$('.untracked_time').css('display', display)
	$('.tracked_time').css('border-radius', border_radius)

	if (value) {
		$('.main_container').css('left', '10%')
		$('.day_date').css('left', '-8%')
		$('.day_date').css('margin-top', '15px')
		$('.time_marker').css('left', '10.3%')
		$('.time_marker').css('position', 'relative')
		$('#current_time_marker').css('display', 'none')

	} else {
		$('.main_container').css('left', '')
		$('.day_date').css('left', '')
		$('.day_date').css('margin-top', '')
		$('.time_marker').css('left', '')
		$('.time_marker').css('position', '')
		$('#current_time_marker').css('display', '')
	}
}

function activate_black_mode(value) {
	client_mode = false
	
	if (value) {
		$('.tracked_time').each(function() {
			$(this).css('background-color', 'black')
		})
	} else {
		activate_client_mode(false)
	}
}

function move_time_marker() {
	$('#current_time_marker').css('left', get_day_percentage() - 0.1 + '%');
}

var DELAY = 200, entry_clicks = 0, timer = null, mousedown = false
// This has all been put into a function so we can call it again after loading elements via AJAX.
function assign_listeners() {
	$('[data-toggle="tooltip"]').tooltip({placement: 'bottom'});
	
	move_time_marker()
	setInterval(move_time_marker, 30000)


	$('.tracked_time').on('mousedown', function(e) {
		entry_clicks++

		clicked_entry_id = $(this).data('id')
		clicked_project = $(this).data('project')
		clicked_client = $(this).data('client')

		mousedown = true

		if (entry_clicks === 1) {
			
			long_click_timeout = setTimeout(function() {
				display_entry_details(clicked_entry_id)
			}, 500)

			short_click_timeout = setTimeout(function() {
				entry_clicks = 0
				if (mousedown) {
					return
				}

				if (e.ctrlKey) {

					if (filter_settings['type'] == 'client') {
						clicked_client = false
					}

					apply_filter('client', clicked_client)

				} else {

					if (filter_settings['type'] == 'project') {
						clicked_project = false
					}

					apply_filter('project', clicked_project)

				}
			}, 200)
		} else {
			// Double click
			entry_clicks = 0

			clearTimeout(short_click_timeout)
			clearTimeout(long_click_timeout)
			

			clicked_description = $(this).data('description')
			apply_filter('description', clicked_description)
		}
	}).on('dblclick', function(e) {
		e.preventDefault()
	}).on('mouseup', function() {
		clearTimeout(long_click_timeout)
		mousedown = false
	})

	// Filtering Days
	var date_clicks = 0, filtering_days = false
	$('.day_date').on('mousedown', function(e){
		date_clicks++

		if(date_clicks===1) {
			target_day = $(this).data('day')
			
			timer = setTimeout(function() {
				date_clicks = 0
				$('.day_date').each(function() {
					if(filtering_days) {
						$(this).parent().show()
					} else {
						if($(this).data('day') != target_day) {
							$(this).parent().hide()
						}
					}
				})

				filtering_days = (filtering_days) ? false : true

			}, DELAY)
		} else {
			clearTimeout(timer)
			date_clicks = 0

			target_date = $(this).data('date')

			$('.day_date').each(function() {
					if(filtering_days) {
						$(this).parent().show()
					} else {
						if($(this).data('date') != target_date) {
							$(this).parent().hide()
						}
					}
				})

			filtering_days = (filtering_days) ? false : true

		}
	})
	.on('dblclick', function(e) {
		e.preventDefault()
	})

}

function display_entry_details(entry_id) {
	console.log('display_entry_details')
	console.log(entry_id)

	var data = {
		'entry_id': entry_id
	}

	$.ajax({
		"type": "POST",
		"url": "/timelines/entry_details",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			console.log(response)

			$container = $('#entry_details_container')
			$container.html(response)

			$('#entry_details_container').show();
			disable_search = true
		}
	})
}

$('body').on('blur', '#journal', function() {
	console.log('update journal')

	var entry_id = $('#entry_id').val()
	var journal = $('#journal').val()

	data = {
		'entry_id': entry_id,
		'journal': journal
	}

	$.ajax({
		"type": "POST",
		"url": "/timelines/update_entry",
		"contentType": "application/json",
		"dataType": "json",
		"data": JSON.stringify(data),
		success: function(response) {
			console.log('updated!')
		}
	})
})

$('body').on('click', '#close_entry_details', function() {
	$('#entry_details_container').hide()
})


function remove_listeners() {
	$('.day_date').off()
	$('.tracked_time').off('click')
}

function apply_filter(type, search_value) {
	// If we're trying to apply a search which is already active, remove the filter.
	if (type == false || search_value == false ) {
		$('.tracked_time').css('opacity', 1)
		update_filter_settings(false, false)
		return false
	}

	search_value = String(search_value).toLowerCase()

	$('.tracked_time').each(function() {

		var entry_value = String($(this).data(type)).toLowerCase()

		if (entry_value.includes(search_value)) {
			$(this).css('opacity', 1)
		} else {
			$(this).css('opacity', 0.15)
		}
	})

	update_filter_settings(type, search_value)
}

function update_filter_settings(type, value) {
	if (type == false || value == false) {
		filter_settings = {
			'active': false,
			'type': false,
			'value': false
		}
	} else {
		filter_settings = {
			'active': true,
			'type': type,
			'value': value
		}
	}
}

$(document).ready(function(){
	assign_listeners()

	$('.timelines_reload').click(function() {
		$.ajax({
			"type": "POST",
			"url": $SCRIPT_ROOT + "/timelines/load_more",
			"contentType": "application/json",
			"dataType": "json",
			"data": JSON.stringify({reload: true}),
			success: function(response) {
				$('.day_row').first().replaceWith(response)
				remove_listeners()
				assign_listeners()
			}
		})
	})
	
	$('.load_more').click(function() {
		load_all = $(this).attr('id') == 'load_all' ? true : false
		
		if (load_all) {
			start_days_ago = false
		}

		data = {
			reload: false,
			start_days_ago: start_days_ago,
			end_days_ago: end_days_ago
		}

		$.ajax($SCRIPT_ROOT + '/timelines/load_more',{
			'type': 'POST',
			"contentType": "application/json",
			'data': JSON.stringify(data),
			'beforeSend': function() {
				if (load_all) {
					$('.load_more').hide()
					$('#loading_div').show()
				}
				
			},
			'complete': function() {
				$('#loading_div').hide()
			}
		}).done(function(data) {
			$('.timeline_container').append(data)
			
			if (load_all) {
				$('#load_more').hide();
				$('#current_time_marker').css('height', 'calc(100% + 10px)');
			}

			if (!load_all) {
				start_days_ago += 7
				end_days_ago += 7
			}

			remove_listeners()
			assign_listeners()

			apply_filter(filter_settings['type'], filter_settings['value'])
		})
	})

	client_mode = false
	black_mode = false
	search_visible = false
	$('body').keypress(function(e) {
		
		if(disable_search) {
			return
		}

		//console.log(e.which)

		/*
		if(e.which==99) { //c key
			client_mode = (client_mode) ? false : true

			activate_client_mode(client_mode)
		}
		*/

		if (e.which==115 && !$('input[name=timeline_search]').is(':focus')) { //s key

			e.preventDefault()

			search_visible = (search_visible) ? false : true
			
			if (search_visible) {
				$('.timeline_search_container').show()
				$('input[name=timeline_search]').prop('disabled', false)
				$('input[name=timeline_search]').focus()
			} else {
				$('.timeline_search_container').hide()
				$('input[name=timeline_search]').prop('disabled', true)
			}
		}

	})

	// Hide the search box when input field is unselected.
	$('input[name=timeline_search]').focusout(function() {
		$('body').trigger(jQuery.Event('keypress', {which: 115}))
	})

	var search_timeout = false
	$('input[name=timeline_search]').on('input', function() {	
		var search_input = this.value.toLowerCase()

		if (search_timeout) {
			clearTimeout(search_timeout)
		}

		search_timeout = setTimeout(function() {
			apply_filter('description', search_input)
		},
		600)
	})
});