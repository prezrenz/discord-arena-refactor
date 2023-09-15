def clamp(num, min, max):
	return min if num < min else max if num > max else num
	
def num_to_alpha(num):
	return chr(num + 96)

def alpha_to_num(ch):
	return ord(ch - 96)