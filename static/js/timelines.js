function get_day_percentage() {
	var now  = new Date()
		then = new Date(
			now.getFullYear(),
			now.getMonth(),
			now.getDate(),
			0, 0, 0
		)

	ms_since_midnight = now.getTime() - then.getTime()
	minutes_since_midnight = ms_since_midnight/60000
	day_percentage = (minutes_since_midnight/(60*24))*100

	return day_percentage
}

var active = {
	'project': [],
	'description': [],
	'client' : []
}

function highlight_category(category, target) {
	if(active[category].length == 1 && active[category][0] == target || !target) {
		active[category] = []
	} else {
		active[category] = [target]
	}

	$('.tracked_time').each(function() {
		if (active[category].includes($(this).data(category)) || active[category].length == 0){
			$(this).css('opacity', 1)
		} else {
			$(this).css('opacity', 0.15)
		}
	})

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
	console.log('black mode')

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

// This has all been put into a function so we can call it again after loading elements via AJAX.
function assign_listeners() {
	var DELAY = 200, entry_clicks = 0, timer = null

	$('[data-toggle="tooltip"]').tooltip({placement: 'bottom'});
	
	move_time_marker()
	setInterval(move_time_marker, 30000)

	// Selecting Projects
	$('.tracked_time').on('click', function(e){
		console.log('CLICK!')
		entry_clicks++
		clicked_project = $(this).data('project')
		clicked_client = $(this).data('client')

		if(entry_clicks===1) {
			
			timer = setTimeout(function() {
				entry_clicks = 0
			
				if (e.ctrlKey) {
					highlight_category('client', clicked_client)
				} else {
					highlight_category('project', clicked_project)
				}
				
			}, DELAY)
		} else {
			clearTimeout(timer)
			entry_clicks = 0

			if(active['project'].length > 0){
				active['project'] = []
				highlight_category('project', false)
			}

			clicked_description = $(this).data('description')
			highlight_category('description', clicked_description)

		}
	})
	.on('dblclick', function(e) {
		e.preventDefault()
	})

	// Filtering Days
	var date_clicks = 0, filtering_days = false
	$('.day_date').on('click', function(e){
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

	// Move date labels if necessary, so they aren't covered by entries shortly after midnight.
	row = 1
	$('.day_row').each(function() {
		total_percentage = 0
		early_tracked_entry = false



		date_element = $(this).children().first()
		number_of_children = $(this).children().length

		child_number = 1
		corrected_date_position = false
		$(this).children('.track_block').each(function() {
			previous_percentage = total_percentage

			additional_percentage = $(this).data('percentage')

			if(typeof additional_percentage == 'string'){
				additional_percentage = parseInt(additional_percentage)
			}

			total_percentage += additional_percentage
			
			if($(this).hasClass('tracked_time')){
				early_tracked_entry = true
			}

			if(!corrected_date_position && total_percentage > 8) { // (Date labels cover about 8% of the width).
				if(early_tracked_entry) {
					
					safe_position = (child_number == 1) ? total_percentage : previous_percentage


					safe_position += 0.5

					date_element.css('left', safe_position + '%')
				}
				corrected_date_position = true

				//return false
				//The section below is to fix an issue of days reaching percentages higher than 100, and final items overflowing to next row. If I can figure out how to fix it via css, that would be better. Then I can uncomment this line to shorten the amount looped.
			}


			if(child_number == number_of_children-1 && row > 1) {	
				overflow_percentage = total_percentage - 100
				current_element_percentage = $(this).data('percentage')
				new_element_percentage = current_element_percentage - overflow_percentage - 0.03
				date = $(this).data('date')

				$(this).css('width', new_element_percentage + '%')
			}
			child_number += 1
		})
		row += 1
	})

}

function remove_listeners() {
	$('.day_date').off()
	$('.tracked_time').off()
}

$(document).ready(function(){
	assign_listeners()
	
	$('#load_more').click(function() {
		$.ajax($SCRIPT_ROOT + '/load_more',{
			'beforeSend': function() {
				$('#load_more').hide()
				$('#loading_div').show()
			},
			'complete': function() {
				$('#loading_div').hide()
			}
		}).done(function(data) {
			$('.main_container').append(data)
			$('#load_more').hide()
			remove_listeners()
			assign_listeners()
		})
	})

	client_mode = false
	stack_mode = false
	black_mode = false
	$('body').keypress(function(e) {
		console.log(e.which)

		if(e.which==99) {
			client_mode = (client_mode) ? false : true

			activate_client_mode(client_mode)
		}

		if (e.which==115) {
			stack_mode = (stack_mode) ? false : true
			
			activate_stack_mode(stack_mode)
		}

		if (e.which==119) {
			black_mode = (black_mode) ? false : true
			
			activate_black_mode(black_mode)
		}

		
	})

});