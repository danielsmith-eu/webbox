
$('#loader').width($(document).width());
WebBox.load().then(function(exports) {
	console.log('exports ', exports);
	$('#loader').fadeOut('slow', function() {
		$('.loaded').slideDown('slow');
		window.store = new WebBox.Store();
	});
});
